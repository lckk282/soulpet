"""运行状态：模块健康、事件流（桌宠/网页订阅）、用量、日志。"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from .. import paths
from ..config_store import get
from ..core import event_bus, usage_meter
from ..core.pet_runtime import get_pet
from ..core.scheduler import running as sched_running
from ..core.scheduler import state_now
from ..schemas import GlobalConfig, PetProfile
from ..secrets_store import get_store
from ..services import module_manager

router = APIRouter(prefix="/api/status", tags=["status"])


@router.get("")
def status():
    gcfg: GlobalConfig = get("global")  # type: ignore[assignment]
    prof: PetProfile = get("pet")  # type: ignore[assignment]
    pet_row = get_pet()
    return {
        "ok": True,
        "state": state_now(),
        "scheduler_running": sched_running(),
        "server_port": gcfg.server.port,
        "secret_backend": get_store().backend_name,
        "pet": {
            "id": prof.pet.id,
            "name": prof.pet.name,
            "status": pet_row.status if pet_row else None,
        },
        "modules": module_manager.status(),
        "usage": usage_meter.summary(prof.pet.id) if prof.pet.id else None,
    }


@router.get("/usage")
def usage():
    prof: PetProfile = get("pet")  # type: ignore[assignment]
    if not prof.pet.id:
        raise HTTPException(409, "还没有创建宠物")
    return {"ok": True, "data": usage_meter.summary(prof.pet.id), "recent": usage_meter.recent(prof.pet.id)}


@router.get("/events")
def events(max_seconds: int = 600):
    """SSE 事件流：桌宠与网页共用。

    有最大时长限制（默认 10 分钟），到点后自动结束，避免长连接线程泄漏；
    客户端（EventSource）会自动重连。
    """

    def gen():
        import time

        yield "data: " + json.dumps({"type": "hello", "history": event_bus.history()[-10:]}, ensure_ascii=False) + "\n\n"
        last = 0
        deadline = time.time() + max(10, min(max_seconds, 3600))
        while time.time() < deadline:
            hist = event_bus.history()
            if len(hist) > last:
                for ev in hist[last:]:
                    yield "data: " + json.dumps(ev, ensure_ascii=False) + "\n\n"
                last = len(hist)
            else:
                yield ": keep-alive\n\n"
            time.sleep(0.5)

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/logs")
def logs(module: str = "backend", lines: int = 100):
    name = "backend.log" if module == "backend" else f"{module}.log"
    p = paths.LOG_DIR / name
    if not p.exists():
        return {"ok": True, "lines": [], "path": str(p)}
    try:
        with p.open("r", encoding="utf-8", errors="ignore") as f:
            content = f.read().splitlines()[-lines:]
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"ok": True, "lines": content, "path": str(p)}


@router.post("/backup")
def backup():
    """打包配置 + 数据库 + 记忆，供用户自己保存。"""
    import shutil
    import tempfile
    from datetime import datetime

    paths.ensure_dirs()
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = paths.BACKUP_DIR / f"soulpet-backup-{ts}"
    try:
        with tempfile.TemporaryDirectory() as td:
            stage = __import__("pathlib").Path(td) / "soulpet"
            stage.mkdir(parents=True)
            shutil.copytree(paths.CONFIG_DIR, stage / "config", dirs_exist_ok=True)
            if paths.DB_PATH.exists():
                shutil.copy2(paths.DB_PATH, stage / "soulpet.db")
            if paths.MEMORY_DIR.exists():
                shutil.copytree(paths.MEMORY_DIR, stage / "memory", dirs_exist_ok=True)
            shutil.make_archive(str(out), "zip", td)
    except Exception as e:
        raise HTTPException(500, f"备份失败：{e}")
    return {"ok": True, "path": str(out) + ".zip"}
