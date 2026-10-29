"""向导 API：草稿存取、服务端二次校验、一次性提交生成整只宠物。"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import shutil
import tempfile
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import paths
from ..config_store import clear_cache, get, set_
from ..schemas import (
    DeployConfig,
    GlobalConfig,
    ModelConfig,
    ModulesConfig,
    PetProfile,
    ScheduleConfig,
    WizardDraft,
    now_iso,
)
from ..secrets_store import get_store

router = APIRouter(prefix="/api/wizard", tags=["wizard"])

log = logging.getLogger("soulpet.wizard")


def _safe_rmtree(target) -> None:
    """删目录，绝不因为删不掉就把整个服务拖下水。

    Windows 上文件被占用时 rmtree 会失败；某些运行环境还会在批量删除时
    直接抛 SystemExit —— 那是 BaseException，`except Exception` 抓不住，
    结果就是「点一下恢复出厂，服务直接退出」。这里连 BaseException 一起兜住。
    """
    try:
        shutil.rmtree(target, ignore_errors=True)
    except BaseException as e:  # noqa: BLE001
        log.warning("清理目录 %s 失败，已跳过：%s", target, e)


# ── 草稿 ────────────────────────────────────────────────────────


def _atomic_write_json(path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


_SECRET_KEYS = {"api_key", "token", "app_secret", "password", "client_secret"}


def _strip_secrets(obj):
    """递归清理：草稿里绝不保存任何密钥真值（含嵌套结构）。

    注意是「删掉这个键」而不是填 "***"：占位符一旦被读回并提交，
    就会被当成真 Key 写进钥匙串，等于给用户塞了一个假密钥。
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in _SECRET_KEYS and v:
                continue
            out[k] = _strip_secrets(v)
        return out
    if isinstance(obj, list):
        return [_strip_secrets(v) for v in obj]
    return obj


@router.get("/draft")
def get_draft():
    cfg: GlobalConfig = get("global")  # type: ignore[assignment]
    data = None
    if paths.DRAFT_PATH.exists():
        try:
            with paths.DRAFT_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = None
    return {
        "ok": True,
        "draft": data,
        "initialized": bool(cfg.wizard.completed),
        "ack": cfg.wizard.ack.model_dump(),
    }


class DraftIn(BaseModel):
    draft: dict


@router.post("/draft")
def save_draft(body: DraftIn):
    data = _strip_secrets(dict(body.draft or {}))
    # 草稿是一次性表单快照，256KB 足够；不设上限的话一个请求就能把磁盘写满
    if len(json.dumps(data, ensure_ascii=False).encode("utf-8")) > 256 * 1024:
        raise HTTPException(413, "草稿过大（上限 256KB）")
    _atomic_write_json(paths.DRAFT_PATH, {"saved_at": now_iso(), "draft": data})
    return {"ok": True, "saved_at": now_iso()}


@router.post("/ack")
def ack(ack: dict):
    cfg: GlobalConfig = get("global")  # type: ignore[assignment]
    cfg.wizard.ack.privacy = bool(ack.get("privacy"))
    cfg.wizard.ack.cost = bool(ack.get("cost"))
    cfg.wizard.ack.risk = bool(ack.get("risk"))
    cfg.wizard.ack.at = now_iso()
    set_("global", cfg)
    return {"ok": True, "ack": cfg.wizard.ack.model_dump()}


# ── 校验 ────────────────────────────────────────────────────────


def validate(draft: dict) -> tuple[dict, list[str], list[str]]:
    """返回 (normalized, errors, warnings)。errors 非空即不允许提交。"""
    errors: list[str] = []
    warnings: list[str] = []

    try:
        d = WizardDraft(**draft)
    except Exception as e:
        return {}, [f"表单数据不合法：{e}"], []

    if not d.ack or not (d.ack.privacy and d.ack.cost and d.ack.risk):
        errors.append("请先阅读并勾选欢迎页的三项知情确认")
    if not d.identity:
        errors.append("缺少基础形象设定")
    elif not d.identity.name.strip():
        errors.append("宠物名字不能为空")
    if not d.personality:
        warnings.append("未设置性格，将使用默认值")
    else:
        # 滑块由 Pydantic 静默钳制到 0~100，这里补一句提示，避免用户以为设置生效了原值
        raw_sl = (draft.get("personality") or {}).get("sliders") or {}
        for key, raw_v in raw_sl.items():
            try:
                iv = int(raw_v)
            except (TypeError, ValueError):
                continue
            clamped = getattr(d.personality.sliders, key, None)
            if clamped is not None and iv != clamped:
                warnings.append(f"性格滑块「{key}」取值 {iv} 超出 0~100，已自动修正为 {clamped}")

        sch = d.personality.schedule
        if sch is not None:
            if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", sch.active_start or ""):
                errors.append(f"每日活跃开始时间应为 HH:MM（如 09:00），当前为「{sch.active_start}」")
            if not 1 <= sch.active_hours <= 24:
                errors.append(f"每日活跃时长应在 1~24 小时之间，当前为 {sch.active_hours}")
            quiet = (sch.proactive.quiet_hours if sch.proactive else None) or []
            if len(quiet) not in (0, 2):
                errors.append("免打扰时段需填 2 个时间点（开始、结束）")
            for q in quiet:
                if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", q or ""):
                    errors.append(f"免打扰时间应为 HH:MM（如 23:00），当前为「{q}」")
    if not d.model:
        errors.append("缺少大模型配置")
    else:
        if not d.model.base_url.startswith(("http://", "https://")):
            errors.append("API 地址必须以 http(s):// 开头")
        if not d.model.api_key:
            warnings.append("未填写 API Key，将以「离线体验模式」启动（随时可在设置里补填）")

    if d.modules and d.modules.desktop_pet and not (d.identity and d.identity.asset_pack_id):
        warnings.append("桌宠已开启但未指定素材包，将使用内置默认形象")

    if d.modules and d.modules.qq:
        if not d.qq:
            errors.append("已开启 QQ 连接器，但未完成 QQ 配置")
        else:
            if d.qq.scheme == "napcat" and not d.qq.ws_url.startswith("ws"):
                errors.append("NapCat 连接地址应为 ws:// 或 wss:// 开头")
            if d.qq.scheme == "official" and not d.qq.app_id:
                errors.append("官方机器人需要填写 AppID")
            if not d.qq.risk_accepted:
                errors.append("请先确认所选 QQ 方案的风险提示")

    if d.deploy and d.deploy.mode == "cloud":
        c = d.deploy.cloud
        if not c or not c.host:
            errors.append("云服部署需要填写主机地址")
        elif not re.match(r"^[A-Za-z0-9.\-]+$", c.host):
            errors.append("主机地址格式不正确（请填域名或 IP）")

    return d.model_dump(), errors, warnings


class ValidateIn(BaseModel):
    draft: dict


@router.post("/validate")
def validate_api(body: ValidateIn):
    _, errors, warnings = validate(body.draft)
    return {"ok": not errors, "errors": errors, "warnings": warnings}


# ── 提交 ────────────────────────────────────────────────────────


def _backup_configs() -> str | None:
    paths.ensure_dirs()
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    zip_path = paths.BACKUP_DIR / f"before-commit-{ts}.zip"
    try:
        base = paths.CONFIG_DIR
        with tempfile.TemporaryDirectory() as td:
            stage = os.path.join(td, "config")
            shutil.copytree(base, stage)
            shutil.make_archive(str(zip_path.with_suffix("")), "zip", td)
        return str(zip_path)
    except Exception:
        return None


class CommitIn(BaseModel):
    draft: dict


@router.post("/commit")
def commit(body: CommitIn):
    d, errors, warnings = validate(body.draft)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors, "warnings": warnings})

    store = get_store()
    steps: list[str] = []

    # 1) 备份
    _backup_configs()
    steps.append("已备份现有配置")

    # 2) global
    gcfg: GlobalConfig = get("global")  # type: ignore[assignment]
    if not gcfg.instance_id:
        gcfg.instance_id = "inst_" + secrets.token_hex(6)
    if not gcfg.installed_at:
        gcfg.installed_at = now_iso()
    gcfg.wizard.completed = True
    gcfg.wizard.ack.privacy = gcfg.wizard.ack.cost = gcfg.wizard.ack.risk = True
    gcfg.wizard.ack.at = gcfg.wizard.ack.at or now_iso()
    set_("global", gcfg)

    # 3) 宠物档案
    ident = d.get("identity") or {}
    pid = "pet_" + secrets.token_hex(4)
    profile = PetProfile()
    profile.pet.id = pid
    profile.pet.name = ident.get("name", "小绫")
    profile.pet.role_presets = ident.get("role_presets") or []
    profile.pet.role_custom = ident.get("role_custom") or ""
    profile.pet.bio = ident.get("bio") or ""
    profile.pet.avatar_pack_id = ident.get("asset_pack_id") or ""
    if d.get("personality"):
        p = d["personality"]
        profile.personality.sliders = type(profile.personality.sliders)(**(p.get("sliders") or {}))
        profile.personality.tags = p.get("tags") or []
        profile.personality.hard_rules = p.get("hard_rules") or []
        from ..core.prompt_builder import map_derived

        derived = map_derived(profile.personality.sliders.model_dump())
        profile.personality.derived = type(profile.personality.derived)(**derived)
        if p.get("schedule"):
            set_("schedule", ScheduleConfig(**p["schedule"]))
    set_("pet", profile)
    steps.append("已写入宠物档案")

    # 4) 部署
    dep = d.get("deploy") or {"mode": "local"}
    dcfg = DeployConfig(mode=dep.get("mode", "local"))
    if dep.get("cloud"):
        dcfg.cloud = type(dcfg.cloud)(**dep["cloud"])
    if dcfg.mode == "cloud":
        gcfg.server.auth_required = True
        set_("global", gcfg)
    set_("deploy", dcfg)

    # 5) 模型 + 密钥
    m = d.get("model") or {}
    mcfg = ModelConfig(
        provider=m.get("provider", "custom"),
        model=m.get("model", ""),
        base_url=m.get("base_url", ""),
    )
    if m.get("pricing"):
        mcfg.pricing = type(mcfg.pricing)(**m["pricing"])
    if m.get("budget"):
        mcfg.budget = type(mcfg.budget)(**m["budget"])
    if m.get("advanced"):
        mcfg.advanced = type(mcfg.advanced)(**m["advanced"])
    mcfg.embedding_enabled = bool(m.get("embedding_enabled"))
    mcfg.embedding_model = m.get("embedding_model") or ""
    if m.get("api_key"):
        store.set("llm_api_key", m["api_key"])
        steps.append("已保存 API Key 到系统钥匙串")
    else:
        warnings.append("未配置 API Key，当前为离线体验模式")
    set_("model", mcfg)

    # 6) 模块
    mods = d.get("modules") or {}
    mconf = ModulesConfig()
    mconf.web_chat = True
    if mods.get("qq") and d.get("qq"):
        q = d["qq"]
        mconf.qq.enabled = True
        mconf.qq.scheme = q.get("scheme", "napcat")
        mconf.qq.ws_url = q.get("ws_url", "ws://127.0.0.1:3001")
        mconf.qq.app_id = q.get("app_id", "")
        mconf.qq.risk_accepted = True
        mconf.qq.risk_accepted_at = now_iso()
        if q.get("groups"):
            mconf.qq.policy.groups = [_group(g) for g in q["groups"]]
        mconf.qq.policy.private_enabled = bool(q.get("private_enabled", True))
        mconf.qq.policy.private_whitelist = q.get("private_whitelist") or []
        if q.get("token"):
            store.set("qq_token", q["token"])
        if q.get("app_secret"):
            store.set("qq_app_secret", q["app_secret"])
    if mods.get("desktop_pet"):
        mconf.desktop_pet.enabled = True
        pa = d.get("pet") or {}
        mconf.desktop_pet.pack_id = pa.get("pack_id") or ident.get("asset_pack_id") or ""
        mconf.desktop_pet.scale = float(pa.get("scale", 1.0) or 1.0)
        mconf.desktop_pet.always_on_top = bool(pa.get("always_on_top", True))
        mconf.desktop_pet.click_through = bool(pa.get("click_through", False))
        mconf.desktop_pet.opacity = int(pa.get("opacity", 100) or 100)
    set_("modules", mconf)
    set_("qq", mconf.qq)
    steps.append("已写入模块配置")

    # 7) 数据库 + seed 记忆
    from ..core import event_bus
    from ..core import scheduler as sched
    from ..core.memory_engine import add
    from ..db import init_db, session
    from ..models import Pet as PetRow

    init_db()
    with session() as s:
        if not s.get(PetRow, pid):
            s.add(PetRow(id=pid, name=profile.pet.name, asset_pack_id=profile.pet.avatar_pack_id))
    add(
        pid,
        f"{datetime.now().strftime('%Y-%m-%d')} 主人创造了我，给我取名叫「{profile.pet.name}」。",
        type_="event",
        importance=1.0,
        emotion="happy",
        source="manual",
    )
    steps.append("已初始化记忆库")

    # 8) 拉起服务
    try:
        sched.start()
        steps.append("作息调度已启动")
    except Exception as e:
        warnings.append(f"调度器启动失败：{e}")

    from ..services import module_manager

    if mconf.qq.enabled:
        ok, msg = module_manager.start("qq")
        (steps if ok else warnings).append(msg)
    if mconf.desktop_pet.enabled:
        ok, msg = module_manager.start("desktop_pet")
        (steps if ok else warnings).append(msg)

    event_bus.publish("state", value=sched.state_now())
    event_bus.publish("emotion", value="happy")
    clear_cache()

    try:
        if paths.DRAFT_PATH.exists():
            paths.DRAFT_PATH.unlink()
    except Exception:
        pass

    return {
        "ok": True,
        "pet_id": pid,
        "redirect": "/chat",
        "steps": steps,
        "warnings": warnings,
    }


def _group(g: dict):
    from ..schemas import QQGroupPolicy

    return QQGroupPolicy(**g)


@router.post("/reset")
def reset(wipe_data: bool = True):
    """回到出厂：清空配置（以及可选的数据库与记忆）。

    前端文案写的是「恢复出厂」，那就必须真的把记忆清掉，不能只删配置留一堆脏数据。
    动手前先整包备份到 data/backups/，用户后悔还能捞回来。
    """
    backup_path = None
    try:
        from .status import _backup_configs

        backup_path = _backup_configs()
    except Exception:
        backup_path = None

    try:
        # 按注册表删，别手写文件名 —— 以前写死 "pet.yaml" 而真实文件叫
        # "pet.profile.yaml"，结果「恢复出厂」根本没清掉宠物档案。
        from ..config_store import _REGISTRY

        for path, _model in _REGISTRY.values():
            if path.exists():
                path.unlink()
        if paths.DRAFT_PATH.exists():
            paths.DRAFT_PATH.unlink()
        clear_cache()

        if wipe_data:
            from ..db import engine, init_db

            # SQLite 在 Windows 上不许删还有连接的文件，先归还连接池
            engine.dispose()
            for suffix in ("", "-wal", "-shm"):
                f = paths.DB_PATH.with_name(paths.DB_PATH.name + suffix)
                if f.exists():
                    f.unlink()
            for d in (paths.MEMORY_DIR, paths.ASSET_DIR):
                if d.exists():
                    _safe_rmtree(d)
            if paths.SECRETS_PATH.exists():
                paths.SECRETS_PATH.unlink()
            store = get_store()
            for k in ("llm_api_key", "qq_token", "qq_app_secret"):
                try:
                    store.delete(k)
                except Exception:
                    pass
            # 立刻重建空库，避免重置后到重启前的一小段时间里接口报「no such table」
            paths.ensure_dirs()
            init_db()
    except Exception as e:
        raise HTTPException(500, f"重置失败：{e}")

    msg = "已恢复出厂设置，请重启服务后重新捏宠"
    if backup_path:
        msg += f"（重置前的数据已备份到 {backup_path}）"
    return {"ok": True, "message": msg, "backup": backup_path, "restart_required": True}
