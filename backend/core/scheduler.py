"""作息调度：活跃 / 待机 / 省钱待机 三态切换 + 每日归档。

用 APScheduler 的 cron 触发器；misfire_grace_time=0 表示开机不补跑，
避免"一开机就被消息轰炸"。
"""
from __future__ import annotations

from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from ..config_store import schedule as schedule_cfg
from . import event_bus, usage_meter
from .pet_runtime import get_pet

_sched: BackgroundScheduler | None = None


def state_now() -> str:
    """根据配置与当前时间判断宠物状态。"""
    cfg = schedule_cfg()
    if get_pet() and usage_meter.is_over_cap(get_pet().id):  # type: ignore[union-attr]
        return "SAVING"
    try:
        h, m = map(int, cfg.active_start.split(":"))
        cur = datetime.now().hour * 60 + datetime.now().minute
        delta = (cur - (h * 60 + m)) % (24 * 60)
        return "ACTIVE" if delta < cfg.active_hours * 60 else "IDLE"
    except Exception:
        return "ACTIVE"


def _tick() -> None:
    st = state_now()
    event_bus.publish("state", value=st, at=datetime.now().isoformat(timespec="seconds"))


def start() -> None:
    global _sched
    if _sched and _sched.running:
        return
    _sched = BackgroundScheduler(timezone=schedule_cfg().timezone)
    # misfire_grace_time=None：服务重启后不补跑错过的任务，避免开机就轰炸
    _sched.add_job(_tick, "cron", minute="*/10", misfire_grace_time=None, id="state_tick", replace_existing=True)
    _sched.add_job(_tick, "cron", hour=0, minute=5, misfire_grace_time=None, id="midnight", replace_existing=True)
    _sched.start()
    _tick()


def stop() -> None:
    global _sched
    if _sched:
        try:
            _sched.shutdown(wait=False)
        except Exception:
            pass
        _sched = None


def running() -> bool:
    return bool(_sched and _sched.running)
