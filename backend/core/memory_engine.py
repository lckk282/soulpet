"""三层记忆引擎。

L1 工作记忆：最近 N 轮对话（存 messages 表，由调用方取）
L2 事件记忆：本模块负责，SQLite + FTS5 全文检索（零额外依赖）
L3 摘要记忆：按天滚动压缩（summaries 逻辑在 api 层按需调用）

检索打分 = 0.5*相关度 + 0.3*重要度 + 0.2*时间衰减
向量检索为可选项（需在模型配置里开启 embedding），失败自动降级为全文检索。
"""

from __future__ import annotations

import json
import math
import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, func, or_, select
from sqlalchemy import update as sa_update

from .. import paths
from ..db import session
from ..models import Memory

# ── 写入 ────────────────────────────────────────────────────────


def _jsonl_path(ts: datetime) -> Path:
    paths.ensure_dirs()
    return paths.MEMORY_DIR / f"events-{ts.strftime('%Y-%m')}.jsonl"


def _fts_upsert(memory_id: int, content: str) -> None:
    try:
        with sqlite3.connect(paths.DB_PATH) as con:
            con.execute("DELETE FROM memory_fts WHERE memory_id=?", (memory_id,))
            con.execute("INSERT INTO memory_fts(memory_id, content) VALUES(?,?)", (memory_id, content))
    except Exception:
        pass


def _fts_delete(memory_id: int) -> None:
    try:
        with sqlite3.connect(paths.DB_PATH) as con:
            con.execute("DELETE FROM memory_fts WHERE memory_id=?", (memory_id,))
    except Exception:
        pass


def add(
    pet_id: str,
    content: str,
    type_: str = "fact",
    importance: float = 0.6,
    emotion: str = "",
    source: str = "inferred",
) -> Memory | None:
    """写入一条记忆。相似内容自动强化（reinforce）而非重复新增。"""
    content = (content or "").strip()
    if not content or len(content) > 2000:
        return None

    with session() as s:
        dup = s.execute(
            select(Memory).where(
                Memory.pet_id == pet_id,
                Memory.archived.is_(False),
                Memory.content == content,
            )
        ).scalar_one_or_none()
        if dup:
            dup.reinforce_count += 1
            dup.importance = min(1.0, dup.importance + 0.05)
            dup.last_recalled_at = datetime.now()
            s.flush()
            return dup

        m = Memory(
            pet_id=pet_id,
            type=type_,
            content=content,
            importance=max(0.0, min(1.0, importance)),
            emotion=emotion,
            source=source,
        )
        s.add(m)
        s.flush()
        mid = m.id
    _fts_upsert(mid, content)
    _append_jsonl(pet_id, mid, type_, content, importance, emotion, source)
    with session() as s:
        return s.get(Memory, mid)


def _append_jsonl(pet_id: str, mid: int, type_: str, content: str, imp: float, emo: str, src: str) -> None:
    try:
        rec = {
            "id": mid,
            "pet_id": pet_id,
            "type": type_,
            "content": content,
            "importance": imp,
            "emotion": emo,
            "source": src,
            "at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        with _jsonl_path(datetime.now()).open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ── 检索 ────────────────────────────────────────────────────────


def _decay(days: float) -> float:
    return math.exp(-0.03 * days)


def search(pet_id: str, query: str, topk: int = 7) -> list[Memory]:
    """先取候选（全文命中 / 置顶 / 最近），再统一打分排序。"""
    q = (query or "").strip()
    now = datetime.now()
    candidates: dict[int, float] = {}

    with session() as s:
        pinned = (
            s.execute(
                select(Memory).where(Memory.pet_id == pet_id, Memory.pinned.is_(True), Memory.archived.is_(False))
            )
            .scalars()
            .all()
        )
        for m in pinned:
            candidates[m.id] = 1.0

        if q:
            try:
                with sqlite3.connect(paths.DB_PATH) as con:
                    rows = con.execute(
                        "SELECT memory_id, bm25(memory_fts) AS score FROM memory_fts WHERE memory_fts MATCH ? "
                        "ORDER BY score LIMIT 40",
                        (q,),
                    ).fetchall()
            except Exception:
                rows = []
            hit_ids = [r[0] for r in rows]
            if hit_ids:
                fts = (
                    s.execute(select(Memory).where(Memory.id.in_(hit_ids), Memory.archived.is_(False))).scalars().all()
                )
                for m in fts:
                    # bm25 越小越相关，映射到 0~1
                    raw = dict(rows).get(m.id, 0.0)
                    candidates[m.id] = max(candidates.get(m.id, 0.0), 1.0 / (1.0 + abs(raw)))

        recent = (
            s.execute(
                select(Memory)
                .where(Memory.pet_id == pet_id, Memory.archived.is_(False))
                .order_by(Memory.created_at.desc())
                .limit(20)
            )
            .scalars()
            .all()
        )
        for m in recent:
            days = max(0.0, (now - m.created_at).total_seconds() / 86400)
            candidates.setdefault(m.id, 0.15 * _decay(days))

        if not candidates:
            return []

        rows2 = s.execute(select(Memory).where(Memory.id.in_(list(candidates)))).scalars().all()
        scored = []
        for m in rows2:
            days = max(0.0, (now - m.created_at).total_seconds() / 86400)
            score = 0.5 * candidates.get(m.id, 0.0) + 0.3 * m.importance + 0.2 * _decay(days)
            scored.append((score, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        picked = [m for _, m in scored[:topk]]
        for m in picked:
            m.last_recalled_at = now
        s.flush()
        return picked


def timeline(
    pet_id: str,
    type_: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
    include_archived: bool = False,
) -> tuple[list[Memory], int]:
    with session() as s:
        cond = [Memory.pet_id == pet_id]
        if not include_archived:
            cond.append(Memory.archived.is_(False))
        if type_:
            cond.append(Memory.type == type_)
        if q:
            like = f"%{q}%"
            cond.append(or_(Memory.content.like(like)))
        total = s.execute(select(func.count(Memory.id)).where(*cond)).scalar() or 0
        rows = (
            s.execute(
                select(Memory)
                .where(*cond)
                .order_by(Memory.pinned.desc(), Memory.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return rows, int(total)


def stats(pet_id: str) -> dict:
    with session() as s:
        base = [Memory.pet_id == pet_id, Memory.archived.is_(False)]
        total = s.execute(select(func.count(Memory.id)).where(*base)).scalar() or 0
        by_type = dict(s.execute(select(Memory.type, func.count(Memory.id)).where(*base).group_by(Memory.type)).all())
        first = s.execute(select(Memory.created_at).where(*base).order_by(Memory.created_at)).first()
        top = s.execute(select(Memory.content).where(*base).order_by(Memory.importance.desc()).limit(3)).scalars().all()
    return {
        "total": int(total),
        "by_type": by_type,
        "first_at": first[0].isoformat(timespec="seconds") if first else None,
        "highlights": list(top),
    }


# ── 编辑 ────────────────────────────────────────────────────────


def update(mid: int, **fields) -> Memory | None:
    allowed = {"content", "type", "importance", "emotion", "pinned", "archived"}
    patch = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not patch:
        return get(mid)
    with session() as s:
        s.execute(sa_update(Memory).where(Memory.id == mid).values(**patch))
    if "content" in patch:
        _fts_upsert(mid, patch["content"])
    return get(mid)


def get(mid: int) -> Memory | None:
    with session() as s:
        return s.get(Memory, mid)


def remove(mid: int) -> bool:
    _fts_delete(mid)
    with session() as s:
        s.execute(delete(Memory).where(Memory.id == mid))
    return True


def forget_all(pet_id: str) -> int:
    with session() as s:
        ids = s.execute(select(Memory.id).where(Memory.pet_id == pet_id)).scalars().all()
        n = len(ids)
        s.execute(delete(Memory).where(Memory.pet_id == pet_id))
    for i in ids:
        _fts_delete(int(i))
    return n


def export_jsonl(pet_id: str) -> list[dict]:
    with session() as s:
        rows = s.execute(select(Memory).where(Memory.pet_id == pet_id)).scalars().all()
        return [
            {
                "type": r.type,
                "content": r.content,
                "importance": r.importance,
                "emotion": r.emotion,
                "source": r.source,
                "pinned": r.pinned,
                "created_at": r.created_at.isoformat(timespec="seconds"),
            }
            for r in rows
        ]


def import_jsonl(pet_id: str, items: Iterable[dict], replace: bool = False) -> int:
    if replace:
        forget_all(pet_id)
    n = 0
    for it in items:
        if add(
            pet_id,
            it.get("content", ""),
            it.get("type", "fact"),
            float(it.get("importance", 0.6)),
            it.get("emotion", ""),
            it.get("source", "manual"),
        ):
            n += 1
    return n
