"""访问口令（云服务器部署时的门禁）。

本地跑只监听 127.0.0.1，天然安全，默认不开。
一旦把服务放到公网（`deploy.mode = cloud`），记忆库就等于摊在互联网上，
所以那时候必须有一个口令兜底。

开启方式（任一）：
  · 设置环境变量 SOULPET_ACCESS_TOKEN=<你自己定的口令>
  · 向导选「云服务器」部署后，启动时自动生成一个口令写进 data/access_token.txt

浏览器访问 http://<host>:8787/?token=<口令> 一次性登录，之后靠 Cookie 免密。
程序调用则用 `Authorization: Bearer <口令>`。
"""

from __future__ import annotations

import hmac
import logging
import os
import secrets
import threading
import time

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse

from . import paths

log = logging.getLogger("soulpet.auth")

COOKIE_NAME = "soulpet_token"
_TOKEN_FILE = paths.DATA_DIR / "access_token.txt"

# 不需要口令就能访问的路径：健康检查（容器探针）、静态资源、登录入口
_PUBLIC_PREFIXES = ("/assets/", "/api/auth/", "/favicon")
_PUBLIC_EXACT = {"/healthz"}

# ── 失败退避：公网实例上口令只有几十位，但没有限速的话可以一直试 ────
_FAIL_LIMIT = 10
_FAIL_WINDOW = 300.0  # 5 分钟内允许的失败次数
_FAIL_BLOCK = 60.0  # 超限后封多久
_fails: dict[str, list[float]] = {}
_fail_lock = threading.Lock()


def _client(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _blocked_for(key: str) -> float:
    """返回剩余封禁秒数，0 表示没被限速。"""
    now = time.time()
    with _fail_lock:
        hits = [t for t in _fails.get(key, []) if now - t < _FAIL_WINDOW]
        if hits:
            _fails[key] = hits
        else:
            _fails.pop(key, None)
        if len(hits) < _FAIL_LIMIT:
            return 0.0
        return max(0.0, _FAIL_BLOCK - (now - hits[-1]))


def _note_fail(key: str) -> None:
    with _fail_lock:
        _fails.setdefault(key, []).append(time.time())


def _clear_fail(key: str) -> None:
    with _fail_lock:
        _fails.pop(key, None)


def _load_token() -> str:
    env = os.environ.get("SOULPET_ACCESS_TOKEN", "").strip()
    if env:
        return env
    try:
        if _TOKEN_FILE.exists():
            t = _TOKEN_FILE.read_text(encoding="utf-8").strip()
            if t:
                return t
    except Exception:
        pass
    return ""


def _save_token(token: str) -> None:
    try:
        _TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        _TOKEN_FILE.write_text(token, encoding="utf-8")
        try:
            os.chmod(_TOKEN_FILE, 0o600)
        except Exception:
            pass
    except Exception as e:  # pragma: no cover - 磁盘异常
        log.warning("写入访问口令失败：%s", e)


def get_token() -> str:
    """当前生效的口令；空字符串表示不启用鉴权。"""
    return _load_token()


def ensure_token(auth_required: bool) -> str:
    """按配置决定是否启用；启用但没有口令时自动生成一个。"""
    if not auth_required:
        return ""
    token = _load_token()
    if token:
        return token
    token = secrets.token_urlsafe(24)
    _save_token(token)
    log.warning(
        "已启用访问口令，本次生成的口令是：%s\n"
        "  请在浏览器打开 http://<主机>:<端口>/?token=%s 登录一次；"
        "也可以用 SOULPET_ACCESS_TOKEN 环境变量固定口令。口令文件：%s",
        token,
        token,
        _TOKEN_FILE,
    )
    return token


def _supplied_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    q = request.query_params.get("token")
    if q:
        return q.strip()
    return request.cookies.get(COOKIE_NAME, "")


async def token_guard(request: Request, call_next):
    token = get_token()
    if not token:
        return await call_next(request)

    path = request.url.path
    if path in _PUBLIC_EXACT or any(path.startswith(p) for p in _PUBLIC_PREFIXES):
        return await call_next(request)

    who = _client(request)
    wait = _blocked_for(who)
    if wait > 0:
        return JSONResponse(
            {"ok": False, "detail": f"口令错误次数过多，请 {int(wait) + 1} 秒后再试", "need_token": True},
            status_code=429,
            headers={"Retry-After": str(int(wait) + 1)},
        )

    supplied = _supplied_token(request)
    if supplied and hmac.compare_digest(supplied, token):
        _clear_fail(who)
        # 用 ?token= 进来的一次性换 Cookie，然后把地址栏里的口令抹掉
        if request.query_params.get("token"):
            target = str(request.url.remove_query_params("token"))
            resp = RedirectResponse(target, status_code=302)
            resp.set_cookie(
                COOKIE_NAME,
                token,
                max_age=30 * 24 * 3600,
                httponly=True,
                samesite="lax",
                secure=request.url.scheme == "https",
            )
            return resp
        return await call_next(request)

    if supplied:
        _note_fail(who)
    if path.startswith("/api/"):
        return JSONResponse(
            {"ok": False, "detail": "需要访问口令：请在地址后加 ?token=你的口令 登录一次", "need_token": True},
            status_code=401,
        )
    # 页面本身放行，让前端能显示「需要口令」而不是一片白
    return await call_next(request)


def token_hint() -> dict:
    """给前端/日志用的非敏感信息：是否启用、口令文件在哪。"""
    enabled = bool(get_token())
    return {
        "auth_enabled": enabled,
        "token_file": str(_TOKEN_FILE) if enabled else "",
    }
