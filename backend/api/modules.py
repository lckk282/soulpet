"""模块开关 API。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config_store import get, set_
from ..schemas import ModulesConfig
from ..services import module_manager

router = APIRouter(prefix="/api/modules", tags=["modules"])


@router.get("")
def list_modules():
    cfg: ModulesConfig = get("modules")  # type: ignore[assignment]
    return {"ok": True, "config": cfg.model_dump(), "status": module_manager.status()}


class ToggleIn(BaseModel):
    enabled: bool
    scheme: str | None = None
    pack_id: str | None = None


@router.post("/{name}/toggle")
def toggle(name: str, body: ToggleIn):
    cfg: ModulesConfig = get("modules")  # type: ignore[assignment]
    if name == "qq":
        cfg.qq.enabled = body.enabled
        if body.scheme:
            cfg.qq.scheme = body.scheme  # type: ignore[assignment]
    elif name == "desktop_pet":
        cfg.desktop_pet.enabled = body.enabled
        if body.pack_id:
            cfg.desktop_pet.pack_id = body.pack_id
    else:
        raise HTTPException(400, f"模块 {name} 不支持开关")
    set_("modules", cfg)
    if body.enabled:
        ok, msg = module_manager.start(name)
    else:
        ok, msg = module_manager.stop(name)
    return {"ok": ok, "message": msg}


@router.post("/{name}/restart")
def restart(name: str):
    ok, msg = module_manager.restart(name)
    return {"ok": ok, "message": msg}
