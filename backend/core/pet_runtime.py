"""宠物运行时：一次对话的完整编排。

链路：取上下文 → 组 Prompt → 调 LLM（流式）→ 落库 → 抽记忆 → 记用量 → 广播事件
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

from sqlalchemy import select

from ..config_store import model as model_cfg
from ..config_store import pet as pet_cfg
from ..config_store import schedule as schedule_cfg
from ..db import session
from ..models import Conversation, Message, Pet
from ..services.llm import get_llm, is_mock
from . import event_bus, usage_meter
from .memory_engine import add, search
from .memory_extractor import llm_extract, rule_extract
from .prompt_builder import build_system_prompt, current_state_line, parse_emotion


def get_pet() -> Pet | None:
    pid = pet_cfg().pet.id
    if not pid:
        return None
    with session() as s:
        return s.get(Pet, pid) or None


def ensure_conv(pet_id: str, channel: str = "web", scene: str = "private", peer_id: str = "owner") -> Conversation:
    with session() as s:
        conv = s.execute(
            select(Conversation).where(
                Conversation.pet_id == pet_id,
                Conversation.channel == channel,
                Conversation.peer_id == peer_id,
            )
        ).scalar_one_or_none()
        if conv:
            return conv
        conv = Conversation(pet_id=pet_id, channel=channel, scene=scene, peer_id=peer_id)
        s.add(conv)
        s.flush()
        cid = conv.id
    with session() as s:
        return s.get(Conversation, cid)


def history(conv_id: int, turns: int = 20) -> list[dict]:
    with session() as s:
        rows = (
            s.execute(select(Message).where(Message.conv_id == conv_id).order_by(Message.id.desc()).limit(turns * 2))
            .scalars()
            .all()
        )
    rows = list(reversed(rows))
    return [{"role": r.role, "content": r.content} for r in rows]


def build_messages(conv_id: int, user_text: str) -> list[dict]:
    profile = pet_cfg()
    sched = schedule_cfg()
    d = profile.personality.derived
    mems = [m.content for m in search(profile.pet.id, user_text, topk=d.memory_topk or 7)]
    system = build_system_prompt(profile, sched, mems, current_state_line(sched))
    msgs = [{"role": "system", "content": system}]
    msgs += history(conv_id, model_cfg().advanced.context_turns)
    msgs.append({"role": "user", "content": user_text})
    return msgs


def _save(conv_id: int, role: str, content: str, emotion: str = "", tin: int = 0, tout: int = 0) -> None:
    with session() as s:
        s.add(
            Message(
                conv_id=conv_id,
                role=role,
                content=content,
                emotion=emotion,
                tokens_in=tin,
                tokens_out=tout,
            )
        )
        conv = s.get(Conversation, conv_id)
        if conv:
            conv.updated_at = datetime.now()
            if role == "user" and not conv.title:
                conv.title = content[:20]


def stream_reply(conv_id: int, user_text: str) -> Iterator[str]:
    """流式生成回复；yield 文本片段。调用方负责包装为 SSE。"""
    profile = pet_cfg()
    pet_id = profile.pet.id
    d = profile.personality.derived
    llm = get_llm()

    if usage_meter.is_over_cap(pet_id):
        yield "[SAVING] 这个月的额度到顶啦，我先安静一会儿，下个月再陪你聊。"
        return

    msgs = build_messages(conv_id, user_text)
    _save(conv_id, "user", user_text)

    sampling = {
        "temperature": d.temperature,
        "top_p": d.top_p,
        "max_tokens": d.max_tokens,
    }

    buf: list[str] = []
    try:
        for piece in llm.stream(msgs, **sampling):
            buf.append(piece)
            yield piece
    except Exception as e:  # 统一兜底，绝不让聊天页白屏
        from ..adapters.llm.openai_compat import HINTS, LLMError

        if isinstance(e, LLMError):
            hint = HINTS.get(e.kind, "调用出错了")
            msg = f"（{hint}）"
        else:
            msg = "（网络或接口异常，我有点卡壳了，稍后再试一次好吗？）"
        buf.append(msg)
        yield msg

    full = "".join(buf)
    emotion, clean = parse_emotion(full)
    tin = usage_meter.estimate_tokens("".join(m.get("content", "") for m in msgs))
    tout = usage_meter.estimate_tokens(clean)
    _save(conv_id, "assistant", clean, emotion, tin, tout)
    usage_meter.record(
        pet_id,
        tin,
        tout,
        estimated=True,
        provider=model_cfg().provider,
        model_name=model_cfg().model,
    )
    event_bus.publish("emotion", value=emotion)
    event_bus.publish("say", text=clean[:200])

    _extract_async(pet_id, user_text, clean, llm)


def _extract_async(pet_id: str, user_text: str, reply: str, llm) -> None:
    """记忆抽取：默认规则；mock 模式下只走规则（省一次无意义调用）。"""
    try:
        items = None
        if not is_mock():
            items = llm_extract(user_text, reply, llm)
        if not items:
            items = rule_extract(user_text, reply)
        threshold = pet_cfg().personality.derived.memory_write_threshold or 0.5
        for it in items:
            if it.get("importance", 0) < threshold:
                continue
            add(
                pet_id,
                it["content"],
                it.get("type", "fact"),
                it.get("importance", 0.6),
                it.get("emotion", ""),
                it.get("source", "inferred"),
            )
            event_bus.publish("memory", content=it["content"][:80])
    except Exception:
        pass


def greeting(pet_id: str) -> str:
    """首次进入聊天页的开场白（seed 记忆已存在，这里生成一句招呼）。"""
    profile = pet_cfg()
    name = profile.pet.name
    if is_mock():
        return f"[happy] 主人你好，我是{name}！从今天起，我就住在这台电脑里啦。"
    llm = get_llm()
    d = profile.personality.derived
    try:
        msgs = build_messages(ensure_conv(pet_id).id, "（用户刚打开聊天窗口，向你打招呼）")
        msgs.append({"role": "user", "content": "用一句话打个招呼，介绍你自己。"})
        out = llm.chat(msgs, temperature=d.temperature, max_tokens=min(d.max_tokens, 200))
        return out.strip()
    except Exception:
        return f"[happy] 你好呀，我是{name}，终于见面了。"
