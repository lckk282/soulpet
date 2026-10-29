"""模型配置 API：注册表、连通测试、保存配置与价格。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..adapters.llm.openai_compat import HINTS, LLMError, OpenAICompatLLM
from ..adapters.llm.registry import load_registry
from ..config_store import get, set_
from ..schemas import ModelConfig, PricingTable
from ..secrets_store import get_store

router = APIRouter(prefix="/api/model", tags=["model"])


@router.get("/registry")
def registry():
    return {"ok": True, "items": load_registry()}


@router.get("")
def get_model():
    cfg: ModelConfig = get("model")  # type: ignore[assignment]
    data = cfg.model_dump()
    data["has_api_key"] = bool(get_store().get("llm_api_key"))
    return {"ok": True, "config": data}


class TestIn(BaseModel):
    base_url: str
    model: str
    api_key: str = ""
    provider: str = "custom"


@router.post("/test")
def test(body: TestIn):
    if not body.base_url.startswith(("http://", "https://")):
        raise HTTPException(400, "API 地址必须以 http(s):// 开头")
    if not body.api_key:
        return {"ok": False, "kind": "nokey", "hint": "未填写密钥，将以离线体验模式运行"}
    cfg = ModelConfig(provider=body.provider, model=body.model, base_url=body.base_url)
    llm = OpenAICompatLLM(cfg, body.api_key)
    try:
        r = llm.ping()
        return {"ok": True, **r}
    except LLMError as e:
        return {"ok": False, "kind": e.kind, "hint": HINTS.get(e.kind, e.detail), "detail": e.detail[:300]}
    finally:
        llm.close()


class SaveIn(BaseModel):
    provider: str = "custom"
    model: str = ""
    base_url: str = ""
    api_key: str = ""
    pricing: dict | None = None
    budget: dict | None = None
    advanced: dict | None = None
    embedding_enabled: bool = False
    embedding_model: str = ""


@router.put("")
def save(body: SaveIn):
    cfg: ModelConfig = get("model")  # type: ignore[assignment]
    cfg.provider = body.provider or cfg.provider
    cfg.model = body.model or cfg.model
    cfg.base_url = body.base_url or cfg.base_url
    if body.pricing:
        cfg.pricing = type(cfg.pricing)(**body.pricing)
    if body.budget:
        cfg.budget = type(cfg.budget)(**body.budget)
    if body.advanced:
        cfg.advanced = type(cfg.advanced)(**body.advanced)
    cfg.embedding_enabled = body.embedding_enabled
    cfg.embedding_model = body.embedding_model or cfg.embedding_model
    if body.api_key:
        get_store().set("llm_api_key", body.api_key)
    set_("model", cfg)
    return {"ok": True, "has_api_key": bool(get_store().get("llm_api_key"))}


@router.delete("/key")
def delete_key():
    get_store().delete("llm_api_key")
    return {"ok": True}


@router.get("/pricing")
def get_pricing():
    return {"ok": True, "pricing": get("pricing").model_dump()}  # type: ignore[union-attr]


@router.put("/pricing")
def save_pricing(body: dict):
    tbl = PricingTable(
        currency=body.get("currency", "CNY"),
        updated_at=body.get("updated_at", ""),
        note=body.get("note", ""),
        models=body.get("models") or {},
    )
    set_("pricing", tbl)
    return {"ok": True}
