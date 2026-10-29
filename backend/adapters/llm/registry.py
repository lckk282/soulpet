"""模型注册表：预设厂商的 OpenAI 兼容端点。

注意：这里只存「连接信息」，不存价格、不判断某个模型当前是否存在。
模型名以厂商后台为准，价格由用户在 config/pricing.yaml 维护。
"""
from __future__ import annotations

import yaml

from ... import paths

BUILTIN = [
    {
        "id": "zhipu",
        "label": "智谱 GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
        "doc": "https://open.bigmodel.cn/",
    },
    {
        "id": "qwen",
        "label": "通义千问 Qwen",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "doc": "https://help.aliyun.com/zh/model-studio/",
    },
    {
        "id": "deepseek",
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "doc": "https://platform.deepseek.com/",
    },
    {
        "id": "openai",
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "doc": "https://platform.openai.com/",
    },
    {
        "id": "ollama",
        "label": "本地 Ollama",
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "qwen2.5:7b",
        "doc": "https://ollama.com/",
    },
    {
        "id": "custom",
        "label": "自定义（OpenAI 兼容 / 聚合网关）",
        "base_url": "",
        "model": "",
        "doc": "",
    },
]


def load_registry() -> list[dict]:
    """用户可在 config/model_registry.yaml 覆盖或追加预设。"""
    items = list(BUILTIN)
    p = paths.MODEL_REGISTRY
    if p.exists():
        try:
            with p.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            extra = data.get("providers") or []
            ids = {i["id"] for i in items}
            for it in extra:
                if it.get("id") in ids:
                    for i in items:
                        if i["id"] == it["id"]:
                            i.update(it)
                elif it.get("id"):
                    items.append(it)
        except Exception:
            pass
    return items


def by_id(pid: str) -> dict | None:
    for it in load_registry():
        if it["id"] == pid:
            return it
    return None
