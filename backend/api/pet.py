"""宠物档案与素材 API。"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from .. import paths
from ..config_store import get, set_
from ..core.prompt_builder import ROLE_PRESETS, TAG_TEXT
from ..schemas import PetProfile
from ..services import asset_pack

router = APIRouter(prefix="/api/pet", tags=["pet"])


@router.get("")
def get_pet_profile():
    prof: PetProfile = get("pet")  # type: ignore[assignment]
    return {
        "ok": True,
        "profile": prof.model_dump(),
        "roles": [{"id": k, "label": v["label"]} for k, v in ROLE_PRESETS.items()],
        "tags": list(TAG_TEXT.keys()),
    }


@router.put("")
def update_profile(body: dict):
    prof: PetProfile = get("pet")  # type: ignore[assignment]
    p = body.get("pet") or {}
    for k in ("name", "bio", "role_custom"):
        if k in p:
            setattr(prof.pet, k, p[k])
    if "role_presets" in p:
        prof.pet.role_presets = list(p["role_presets"])
    if "avatar_pack_id" in p:
        prof.pet.avatar_pack_id = p["avatar_pack_id"]
    per = body.get("personality") or {}
    if "sliders" in per:
        for k, v in per["sliders"].items():
            if hasattr(prof.personality.sliders, k):
                setattr(prof.personality.sliders, k, max(0, min(100, int(v))))
        from ..core.prompt_builder import map_derived

        prof.personality.derived = type(prof.personality.derived)(**map_derived(prof.personality.sliders.model_dump()))
    for k in ("tags", "hard_rules"):
        if k in per:
            setattr(prof.personality, k, list(per[k]))
    set_("pet", prof)
    return {"ok": True, "profile": prof.model_dump()}


@router.get("/packs")
def list_packs():
    asset_pack.ensure_default_pack()
    items = asset_pack.packs()
    out = []
    for it in items:
        rep = asset_pack.validate_pack(Path(it["path"]))
        out.append({**it, "complete": rep["complete"], "missing": rep["missing_labels"]})
    return {"ok": True, "items": out}


@router.get("/packs/{pack_id}")
def pack_detail(pack_id: str):
    d = paths.ASSET_DIR / pack_id
    if not d.exists():
        raise HTTPException(404, "素材包不存在")
    rep = asset_pack.validate_pack(d)
    manifest = {}
    try:
        manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"ok": True, "report": rep, "manifest": manifest, "pack_id": pack_id}


@router.get("/packs/{pack_id}/file/{name}")
def pack_file(pack_id: str, name: str):
    """素材文件（桌宠与预览用）。禁止 ../ 穿越。"""
    if ".." in name or "/" in name or "\\" in name:
        raise HTTPException(400, "非法文件名")
    p = paths.ASSET_DIR / pack_id / name
    if not p.exists():
        raise HTTPException(404, "文件不存在")
    from fastapi.responses import FileResponse

    media = "image/svg+xml" if p.suffix == ".svg" else "image/png"
    return FileResponse(p, media_type=media)


@router.post("/packs/upload")
async def upload_pack(file: UploadFile = File(...)):
    """上传素材包 zip。限 20MB，解压防路径穿越。"""
    import secrets

    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(400, "请上传 .zip 素材包")
    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(400, "素材包超过 20MB")

    pid = "pack_" + secrets.token_hex(4)
    paths.ensure_dirs()
    tmp = paths.ASSET_DIR / f"{pid}.zip"
    tmp.write_bytes(data)
    dest = paths.ASSET_DIR / pid
    try:
        asset_pack.safe_extract(tmp, dest)
    except Exception as e:
        raise HTTPException(400, f"解压失败：{e}")
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass

    rep = asset_pack.validate_pack(dest)
    return {"ok": True, "pack_id": pid, "report": rep}
