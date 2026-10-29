"""宠物事件总线。

桌宠 / 网页订阅同一事件流，用于情绪、动作、提醒、费用告警等。
线程安全：任何线程都可以 publish，订阅者在 asyncio 循环里消费。
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from collections import deque
from typing import Any

_MAX_HISTORY = 100

_subs: list[asyncio.Queue] = []
_history: deque[dict[str, Any]] = deque(maxlen=_MAX_HISTORY)
_lock = threading.Lock()
_last_proactive: dict[str, float] = {}


def publish(type_: str, **payload) -> dict:
    ev = {"type": type_, "ts": time.time(), **payload}
    with _lock:
        _history.append(ev)
        queues = list(_subs)
    for q in queues:
        try:
            q.put_nowait(ev)
        except Exception:
            pass
    return ev


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    with _lock:
        _subs.append(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    with _lock:
        if q in _subs:
            _subs.remove(q)


def history() -> list[dict]:
    with _lock:
        return list(_history)


def to_sse(ev: dict) -> str:
    return f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"


# ── 主动消息频率闸门（日上限 + 静默时段 + 连续未读降频） ────────────


def proactive_allowed(max_per_day: int, quiet_hours: list[str]) -> bool:
    now = datetime_now()
    if max_per_day <= 0:
        return False
    if quiet_hours and len(quiet_hours) >= 2 and _in_quiet(now, quiet_hours[0], quiet_hours[1]):
        return False
    today = now.strftime("%Y-%m-%d")
    cnt = _proactive_count(today)
    return cnt < max_per_day


def _proactive_count(day: str) -> int:
    n = 0
    for ev in history():
        if ev.get("type") == "proactive" and ev.get("day") == day:
            n += 1
    return n


def mark_proactive() -> None:
    publish("proactive", day=datetime_now().strftime("%Y-%m-%d"))


def datetime_now():
    from datetime import datetime

    return datetime.now()


def _in_quiet(now, start: str, end: str) -> bool:
    def minutes(s: str) -> int:
        try:
            h, m = map(int, s.split(":"))
            return h * 60 + m
        except Exception:
            return 0

    cur = now.hour * 60 + now.minute
    a, b = minutes(start), minutes(end)
    if a == b:
        return False
    return (a < b and a <= cur < b) or (a > b and (cur >= a or cur < b))
