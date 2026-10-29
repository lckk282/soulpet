"""LLM 实例工厂。

· 正常模式：读 config/model.yaml + 钥匙串里的 Key，构造 OpenAI 兼容适配器
· 体验模式（provider=mock 或没有 Key）：使用内置离线回复，零配置也能跑通全流程
"""
from __future__ import annotations

from ..adapters.llm.mock import build_mock
from ..adapters.llm.openai_compat import OpenAICompatLLM
from ..config_store import model as model_cfg
from ..config_store import pet as pet_cfg
from ..secrets_store import get_store


class LLMUnavailable(Exception):
    pass


def api_key() -> str:
    cfg = model_cfg()
    ref = (cfg.api_key_ref or "").strip()
    if ref.startswith("keyring://"):
        key = ref.rsplit("/", 1)[-1]
        return get_store().get(key) or ""
    return ""


def get_llm():
    cfg = model_cfg()
    profile = pet_cfg()
    if cfg.provider == "mock" or not cfg.model or not cfg.base_url:
        return build_mock(profile.pet.role_presets)
    key = api_key()
    if not key:
        # 没填 Key 时不要报错崩掉，降级到体验模式并在状态里提示
        return build_mock(profile.pet.role_presets)
    return OpenAICompatLLM(cfg, key)


def is_mock() -> bool:
    cfg = model_cfg()
    return cfg.provider == "mock" or not cfg.model or not cfg.base_url or not api_key()
