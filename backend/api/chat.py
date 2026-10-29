"""聊天 API。POST /api/chat 返回 SSE 流（前端逐字渲染）。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..config_store import pet as pet_cfg
from ..core.pet_runtime import ensure_conv, greeting, history, stream_reply
from ..db import session
from ..models import Conversation, Message
from ..schemas import ChatRequest

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _require_pet() -> str:
    pid = pet_cfg().pet.id
    if not pid:
        raise HTTPException(409, "还没有创建宠物，请先完成向导")
    return pid


@router.post("")
def chat(req: ChatRequest):
    pet_id = _require_pet()
    conv_id = req.conv_id or ensure_conv(pet_id).id

    # 逐段推送，前端逐字渲染（打字机效果）
    def safe_gen():
        try:
            for piece in stream_reply(conv_id, req.text):
                if not piece:
                    continue
                yield "data: " + _json_one({"delta": piece}) + "\n\n"
        except Exception as e:
            yield "data: " + _json_one({"error": str(e)}) + "\n\n"
        yield "data: " + _json_one({"done": True, "conv_id": conv_id}) + "\n\n"

    return StreamingResponse(safe_gen(), media_type="text/event-stream")


def _json_one(obj: dict) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False)


@router.get("/history")
def get_history(conv_id: int | None = None, limit: int = 100):
    pet_id = _require_pet()
    cid = conv_id or ensure_conv(pet_id).id
    rows = history(cid, turns=limit)
    return {"ok": True, "conv_id": cid, "messages": rows}


@router.get("/conversations")
def list_conversations():
    pet_id = _require_pet()
    with session() as s:
        rows = (
            s.query(Conversation)
            .filter(Conversation.pet_id == pet_id)
            .order_by(Conversation.updated_at.desc())
            .limit(20)
            .all()
        )
        return {
            "ok": True,
            "items": [
                {"id": r.id, "title": r.title or "新对话", "channel": r.channel, "updated_at": r.updated_at.isoformat(timespec="seconds")}
                for r in rows
            ],
        }


@router.delete("/{conv_id}")
def delete_conv(conv_id: int):
    from sqlalchemy import delete

    with session() as s:
        s.execute(delete(Message).where(Message.conv_id == conv_id))
        s.execute(delete(Conversation).where(Conversation.id == conv_id))
    return {"ok": True}


@router.get("/greeting")
def get_greeting():
    pet_id = _require_pet()
    return {"ok": True, "text": greeting(pet_id)}
