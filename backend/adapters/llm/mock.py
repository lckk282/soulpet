"""内置离线回复（Mock LLM）。

目的：让用户下载仓库、双击启动，就能在没有 API Key 的情况下
完整走通「向导 → 聊天 → 记忆 → 桌宠」全流程，确认喜欢之后再填 Key。
"""
from __future__ import annotations

import random
from collections.abc import Iterator

from .openai_compat import LLMError

OPENERS = {
    "maid": "主人~",
    "silent_npc": "...",
    "buddy": "嘿！",
    "cold_assistant": "嗯。",
    "tsundere_cat": "哼，",
    "senior": "我在。",
}

TEMPLATES = [
    "{opener}你说「{q}」啊，我记住了。",
    "{opener}「{q}」——这个我会好好记在小本本上的。",
    "{opener}嗯嗯，关于「{q}」，我想多听你说一点。",
    "{opener}「{q}」……好啦好啦，我知道了，别催。",
    "{opener}收到：「{q}」。要不要我帮你拆成几步？",
]


class MockLLM:
    """接口与 OpenAICompatLLM 保持一致（ping / stream / chat / embed）。"""

    def __init__(self, role: str = ""):
        self.role = role

    def ping(self) -> dict:
        return {"ok": True, "base_url": "mock://local", "model": "soulpet-mock", "latency_ms": 1}

    def chat(self, messages: list[dict], **override) -> str:
        return "".join(self.stream(messages, **override))

    def stream(self, messages: list[dict], **override) -> Iterator[str]:
        user_text = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_text = m.get("content", "")
                break
        q = user_text.strip().replace("\n", " ")[:24]
        opener = OPENERS.get(self.role, "")
        body = random.choice(TEMPLATES).format(opener=opener, q=q)
        # 模拟流式：逐字吐出，让前端 SSE 与打字机效果可验证
        for ch in body:
            yield ch

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        return None

    def close(self) -> None:
        pass


def build_mock(role_presets: list[str]) -> MockLLM:
    return MockLLM(role_presets[0] if role_presets else "")


__all__ = ["MockLLM", "build_mock", "LLMError"]
