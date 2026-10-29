"""QQ 桥接子进程入口（可选模块）。

独立进程运行，崩了不影响主服务。职责：
  收 OneBot11 事件 → 过风控闸门 → 调主服务 /api/chat → 回发消息

启动：python -m backend.adapters.qq.bridge_process
依赖：websockets + httpx（pip install -r requirements-qq.txt）
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import httpx  # noqa: E402

from backend.adapters.qq.base import AutonomyGuard, Target  # noqa: E402
from backend.adapters.qq.napcat import NapCatAdapter  # noqa: E402
from backend.config_store import get  # noqa: E402
from backend.schemas import GlobalConfig, QQConfig  # noqa: E402
from backend.secrets_store import get_store  # noqa: E402

log = logging.getLogger("qq-bridge")


def load_cfg() -> QQConfig:
    return get("qq")  # type: ignore[return-value]


async def reply_text(text: str, peer: str, scene: str) -> str:
    g: GlobalConfig = get("global")  # type: ignore[assignment]
    url = f"http://127.0.0.1:{g.server.port}/api/chat"
    payload = {"text": text, "stream": False}
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(url, json=payload)
            if r.status_code >= 400:
                return "（我这会儿有点懵，等一下再问我？）"
            data = r.json()
            return str(data.get("text", "")).strip()
    except Exception:
        return "（连不上我的小脑袋了，稍后再试~）"


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_cfg()
    if not cfg.enabled:
        log.info("QQ 模块未启用，退出")
        return
    if cfg.scheme != "napcat":
        log.info("当前方案 %s 尚未内置桥接实现，退出", cfg.scheme)
        return

    token = get_store().get("qq_token") or ""
    adapter = NapCatAdapter(cfg.ws_url, token)
    guard = AutonomyGuard(cfg.policy.model_dump())

    await adapter.connect()
    log.info("已连接 NapCat：%s", cfg.ws_url)

    async for msg in adapter.events():
        if not msg.text:
            continue
        ok, why = guard.allow(msg)
        if not ok:
            log.debug("忽略(%s)：%s", why, msg.text[:30])
            continue
        target = Target(scene=msg.scene, id=msg.group_id or msg.user_id)
        try:
            out = await reply_text(msg.text, target.id, msg.scene)
            await adapter.send_text(target, out or "……")
            guard.breaker.reset()
        except Exception as e:
            guard.breaker.fail()
            log.warning("发送失败：%s", e)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
