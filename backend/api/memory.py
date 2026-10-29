"""记忆 API：时间线、统计、增删改、置顶、遗忘、导入导出。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config_store import pet as pet_cfg
from ..core import memory_engine as mem

router = APIRouter(prefix="/api/memory", tags=["memory"])


def _pet_id() -> str:
    pid = pet_cfg().pet.id
    if not pid:
        raise HTTPException(409, "还没有创建宠物")
    return pid


class AddIn(BaseModel):
    content: str
    type: str = "fact"
    importance: float = 0.6
    emotion: str = ""


class UpdateIn(BaseModel):
    content: str | None = None
    type: str | None = None
    importance: float | None = None
    emotion: str | None = None
    pinned: bool | None = None


def _clamp(v: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(int(v), hi))
    except (TypeError, ValueError):
        return lo


@router.get("/timeline")
def timeline(type: str | None = None, q: str | None = None, limit: int = 50, offset: int = 0):
    # 不夹紧的话 ?limit=100000 会把整库一次捞进内存
    rows, total = mem.timeline(
        _pet_id(), type_=type, q=q, limit=_clamp(limit, 1, 200), offset=max(0, _clamp(offset, 0, 1_000_000))
    )
    return {
        "ok": True,
        "total": total,
        "items": [
            {
                "id": r.id,
                "type": r.type,
                "content": r.content,
                "importance": r.importance,
                "emotion": r.emotion,
                "source": r.source,
                "pinned": r.pinned,
                "reinforce_count": r.reinforce_count,
                "created_at": r.created_at.isoformat(timespec="seconds"),
            }
            for r in rows
        ],
    }


@router.get("/stats")
def stats():
    return {"ok": True, "data": mem.stats(_pet_id())}


@router.post("")
def add(body: AddIn):
    m = mem.add(_pet_id(), body.content, body.type, body.importance, body.emotion, source="manual")
    if not m:
        raise HTTPException(400, "内容为空或过长")
    return {"ok": True, "id": m.id}


def _own(mid: int):
    """记忆必须属于当前宠物，避免传别人的 id 越权改删。"""
    m = mem.get(mid)
    if not m or m.pet_id != _pet_id():
        raise HTTPException(404, "记忆不存在")
    return m


@router.put("/{mid}")
def update(mid: int, body: UpdateIn):
    _own(mid)
    m = mem.update(mid, **body.model_dump())
    if not m:
        raise HTTPException(404, "记忆不存在")
    return {"ok": True}


@router.delete("/{mid}")
def delete(mid: int):
    _own(mid)
    mem.remove(mid)
    return {"ok": True}


@router.get("/search")
def search(q: str = "", topk: int = 7):
    rows = mem.search(_pet_id(), q, topk=_clamp(topk, 1, 20))
    return {"ok": True, "items": [{"id": r.id, "content": r.content, "type": r.type} for r in rows]}


@router.get("/export")
def export():
    return {"ok": True, "pet_id": _pet_id(), "items": mem.export_jsonl(_pet_id())}


class ImportIn(BaseModel):
    items: list[dict]
    replace: bool = False


@router.post("/import")
def import_(body: ImportIn):
    if len(body.items) > 5000:
        raise HTTPException(400, "一次最多导入 5000 条记忆")
    n = mem.import_jsonl(_pet_id(), body.items, replace=body.replace)
    return {"ok": True, "imported": n, "skipped": len(body.items) - n}


@router.delete("")
def forget_all():
    n = mem.forget_all(_pet_id())
    return {"ok": True, "deleted": n}
