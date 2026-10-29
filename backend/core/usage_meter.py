"""用量与费用计量。

费用 = tokens × pricing.yaml 中的单价（元/百万 tokens）。
厂商流式返回可能不含 usage，此时按中文约 1.6 字符/token 估算，并记为 is_estimated=1。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select

from ..config_store import model as model_cfg
from ..config_store import pricing as pricing_cfg
from ..db import session
from ..models import UsageLog


def estimate_tokens(text: str) -> int:
    """粗略估算中文 token 数（用于厂商未返回 usage 时兜底）。"""
    if not text:
        return 0
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    other = len(text) - cjk
    return int(cjk / 1.6 + other / 4) + 1


def unit_prices() -> tuple[float, float]:
    cfg = model_cfg()
    p = cfg.pricing
    if p.source != "unknown" and (p.input_per_mtokens or p.output_per_mtokens):
        return p.input_per_mtokens, p.output_per_mtokens
    table = pricing_cfg().models
    key = f"{cfg.provider}/{cfg.model}"
    got = table.get(key) or table.get(cfg.model) or {}
    return float(got.get("input", 0.0)), float(got.get("output", 0.0))


def cost_of(tin: int, tout: int) -> float:
    pi, po = unit_prices()
    return round(tin / 1_000_000 * pi + tout / 1_000_000 * po, 6)


def record(
    pet_id: str,
    tin: int,
    tout: int,
    estimated: bool = False,
    provider: str = "",
    model_name: str = "",
) -> float:
    cfg = model_cfg()
    c = cost_of(tin, tout)
    with session() as s:
        s.add(
            UsageLog(
                pet_id=pet_id,
                provider=provider or cfg.provider,
                model=model_name or cfg.model,
                tokens_in=tin,
                tokens_out=tout,
                cost_estimated=c,
                is_estimated=estimated,
            )
        )
    return c


def _sum_since(s, pet_id: str, since: datetime) -> tuple[int, int, float]:
    row = s.execute(
        select(
            func.coalesce(func.sum(UsageLog.tokens_in), 0),
            func.coalesce(func.sum(UsageLog.tokens_out), 0),
            func.coalesce(func.sum(UsageLog.cost_estimated), 0.0),
        ).where(UsageLog.pet_id == pet_id, UsageLog.created_at >= since)
    ).first()
    return int(row[0] or 0), int(row[1] or 0), float(row[2] or 0.0)


def summary(pet_id: str) -> dict:
    now = datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = day_start.replace(day=1)
    with session() as s:
        d_in, d_out, d_cost = _sum_since(s, pet_id, day_start)
        m_in, m_out, m_cost = _sum_since(s, pet_id, month_start)
        total_in, total_out, total_cost = _sum_since(s, pet_id, datetime(2000, 1, 1))
    cfg = model_cfg()
    return {
        "today": {"tokens_in": d_in, "tokens_out": d_out, "cost": round(d_cost, 4)},
        "month": {"tokens_in": m_in, "tokens_out": m_out, "cost": round(m_cost, 4)},
        "total": {"tokens_in": total_in, "tokens_out": total_out, "cost": round(total_cost, 4)},
        "budget": {
            "daily_warn_cny": cfg.budget.daily_warn_cny,
            "monthly_cap_cny": cfg.budget.monthly_cap_cny,
            "warn": d_cost >= cfg.budget.daily_warn_cny > 0,
            "capped": cfg.budget.auto_idle_on_cap and m_cost >= cfg.budget.monthly_cap_cny > 0,
        },
        "pricing_known": unit_prices() != (0.0, 0.0),
    }


def is_over_cap(pet_id: str) -> bool:
    """月上限触发 → 宠物进入省钱待机，不再调用 LLM。"""
    return bool(summary(pet_id)["budget"]["capped"])


def recent(pet_id: str, days: int = 14) -> list[dict]:
    since = datetime.now() - timedelta(days=days)
    with session() as s:
        rows = s.execute(
            select(UsageLog.created_at, func.sum(UsageLog.cost_estimated))
            .where(UsageLog.pet_id == pet_id, UsageLog.created_at >= since)
            .group_by(func.date(UsageLog.created_at))
            .order_by(func.date(UsageLog.created_at))
        ).all()
    return [{"date": str(r[0])[:10], "cost": round(float(r[1] or 0), 4)} for r in rows]
