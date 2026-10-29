"""NapCat / Lagrange 适配器（OneBot11 标准，正向 WebSocket）。

本项目不实现任何 QQ 协议，只与用户自己部署的 NapCat 通过 OneBot11 通信。
依赖：websockets（pip install -r requirements-qq.txt）
"""
from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator

from .base import BridgeAdapter, Target, UnifiedMessage


class NapCatAdapter(BridgeAdapter):
    name = "napcat"

    def __init__(self, ws_url: str, token: str = "", self_id: str = "", heartbeat_sec: int = 30):
        self.ws_url = ws_url
        self.token = token
        self.self_id = str(self_id or "")
        self.heartbeat_sec = heartbeat_sec
        self.ws = None
        self._backoff = 1
        self._last_heartbeat = 0.0
        self._queue: list[dict] = []

    async def connect(self) -> None:
        import asyncio

        import websockets

        while True:
            try:
                headers = {"Authorization": f"Bearer {self.token}"} if self.token else None
                self.ws = await websockets.connect(
                    self.ws_url, extra_headers=headers, ping_interval=self.heartbeat_sec, ping_timeout=10
                )
                self._backoff = 1
                self._last_heartbeat = time.time()
                return
            except Exception:
                await asyncio.sleep(self._backoff)
                self._backoff = min(self._backoff * 2, 60)

    async def disconnect(self) -> None:
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None

    async def events(self) -> AsyncIterator[UnifiedMessage]:
        if not self.ws:
            await self.connect()
        async for raw in self.ws:  # type: ignore[union-attr]
            try:
                ev = json.loads(raw)
            except Exception:
                continue
            if ev.get("post_type") == "meta_event":
                self._last_heartbeat = time.time()
                continue
            msg = self.normalize(ev)
            if msg:
                yield msg

    def normalize(self, ev: dict) -> UnifiedMessage | None:
        if ev.get("post_type") != "message":
            return None
        segs = ev.get("message", []) or []
        if isinstance(segs, str):
            text, images = segs, []
        else:
            text = "".join(s.get("data", {}).get("text", "") for s in segs if s.get("type") == "text")
            images = [
                s.get("data", {}).get("url") or s.get("data", {}).get("file", "")
                for s in segs
                if s.get("type") == "image"
            ]
        at_me = any(
            s.get("type") == "at" and str(s.get("data", {}).get("qq")) == str(ev.get("self_id", self.self_id))
            for s in segs
            if isinstance(s, dict)
        )
        scene = "group" if ev.get("message_type") == "group" else "private"
        return UnifiedMessage(
            scheme="napcat",
            scene=scene,
            group_id=str(ev.get("group_id")) if ev.get("group_id") else None,
            user_id=str(ev.get("user_id", "")),
            msg_id=str(ev.get("message_id", "")),
            text=(text or "").strip(),
            images=images,
            is_at_me=at_me or scene == "private",
            raw=ev,
        )

    async def _call(self, action: str, params: dict) -> None:
        if not self.ws:
            raise RuntimeError("未连接")
        await self.ws.send(json.dumps({"action": action, "params": params}))

    async def send_text(self, target: Target, text: str) -> None:
        seg = [{"type": "text", "data": {"text": text}}]
        if target.scene == "group":
            await self._call("send_group_msg", {"group_id": int(target.id), "message": seg})
        else:
            await self._call("send_private_msg", {"user_id": int(target.id), "message": seg})

    def health(self) -> dict:
        stale = time.time() - self._last_heartbeat if self._last_heartbeat else 9999
        return {"ok": self.ws is not None and stale < 90, "heartbeat_age": int(stale)}
