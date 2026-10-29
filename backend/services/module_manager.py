"""模块管理：QQ 连接器 / 桌面桌宠 / 网页聊天的启停与健康状态。

设计：子模块独立进程或独立任务，崩了不影响主聊天；状态落 module_status 表，
前端「运行状态」面板直接读。
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from .. import paths
from ..config_store import modules as modules_cfg
from ..db import session
from ..models import ModuleStatus

MODULES = ("qq", "desktop_pet", "web_chat")


def _row(name: str) -> ModuleStatus:
    with session() as s:
        r = s.get(ModuleStatus, name)
        if not r:
            r = ModuleStatus(module=name)
            s.add(r)
            s.flush()
        return r


def _set(name: str, **kw) -> None:
    with session() as s:
        r = s.get(ModuleStatus, name) or ModuleStatus(module=name)
        for k, v in kw.items():
            setattr(r, k, v)
        r.last_heartbeat = datetime.now()
        s.merge(r)


def status() -> dict:
    cfg = modules_cfg()
    out = {}
    for name in MODULES:
        r = _row(name)
        enabled = {"qq": cfg.qq.enabled, "desktop_pet": cfg.desktop_pet.enabled, "web_chat": True}[name]
        out[name] = {
            "enabled": enabled,
            "status": r.status if enabled else "disabled",
            "last_error": r.last_error,
            "last_heartbeat": r.last_heartbeat.isoformat(timespec="seconds") if r.last_heartbeat else None,
            "detail": _detail(name),
        }
    return out


def _detail(name: str) -> str:
    if name == "qq":
        cfg = modules_cfg().qq
        if not cfg.enabled:
            return "未启用"
        return f"方案 {cfg.scheme}"
    if name == "desktop_pet":
        cfg = modules_cfg().desktop_pet
        if not cfg.enabled:
            return "未启用"
        return f"素材包 {cfg.pack_id or '默认'}"
    return "网页聊天始终可用"


def start(name: str) -> tuple[bool, str]:
    cfg = modules_cfg()
    if name == "web_chat":
        _set("web_chat", enabled=True, status="running", last_error="")
        return True, "网页聊天已就绪"
    if name == "qq":
        if not cfg.qq.enabled:
            return False, "QQ 模块未启用"
        return _start_qq()
    if name == "desktop_pet":
        if not cfg.desktop_pet.enabled:
            return False, "桌宠模块未启用"
        _set("desktop_pet", enabled=True, status="waiting", last_error="桌宠为独立桌面程序，请在桌面端启动后自动连接")
        return True, "已开放桌宠连接通道（/pet）"
    return False, f"未知模块 {name}"


def stop(name: str) -> tuple[bool, str]:
    if name == "desktop_pet":
        _set("desktop_pet", enabled=False, status="stopped", last_error="")
        return True, "已停止桌宠通道"
    if name == "qq":
        return _stop_qq()
    return True, "ok"


def _bridge_script() -> Path:
    return paths.APP_ROOT / "backend" / "adapters" / "qq" / "bridge_process.py"


def _start_qq() -> tuple[bool, str]:
    script = _bridge_script()
    if not script.exists():
        _set("qq", enabled=True, status="error", last_error="桥接脚本缺失")
        return False, "桥接脚本缺失"
    try:
        proc = subprocess.Popen(
            [sys.executable, str(script)],
            cwd=str(paths.APP_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        _set("qq", enabled=True, status="error", last_error=str(e))
        return False, str(e)
    _set("qq", enabled=True, status="starting", last_error="", pid=proc.pid)
    return True, f"QQ 桥接进程已启动（pid={proc.pid}）"


def _stop_qq() -> tuple[bool, str]:
    r = _row("qq")
    pid = r.pid or 0
    if pid:
        try:
            import os
            import signal

            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
    _set("qq", enabled=False, status="stopped", last_error="", pid=0)
    return True, "QQ 连接器已断开"


def restart(name: str) -> tuple[bool, str]:
    stop(name)
    return start(name)
