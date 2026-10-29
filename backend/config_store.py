"""配置读写。

原则：
  · 原子写（tmp + replace），断电/崩溃不会写出半个文件
  · 修改前自动备份 .bak
  · 缺文件用默认值生成，读坏文件回退默认 + 备份坏文件（不让用户卡死）
  · 密钥永不进入本文件，只存 keyring:// 引用
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from . import paths
from .schemas import (
    DeployConfig,
    GlobalConfig,
    ModelConfig,
    ModulesConfig,
    PetProfile,
    PricingTable,
    QQConfig,
    ScheduleConfig,
)

T = TypeVar("T", bound=BaseModel)

# 文件 → 模型 映射
_REGISTRY: dict[str, tuple[Path, type[BaseModel]]] = {
    "global": (paths.GLOBAL_CONFIG, GlobalConfig),
    "pet": (paths.PET_PROFILE, PetProfile),
    "schedule": (paths.SCHEDULE_CONFIG, ScheduleConfig),
    "deploy": (paths.DEPLOY_CONFIG, DeployConfig),
    "model": (paths.MODEL_CONFIG, ModelConfig),
    "modules": (paths.MODULES_CONFIG, ModulesConfig),
    "qq": (paths.QQ_CONFIG, QQConfig),
    "pricing": (paths.PRICING_CONFIG, PricingTable),
}


def _read_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    tmp.replace(path)


def load(name: str, model: type[T]) -> T:
    path = _REGISTRY.get(name, (None, model))[0]
    if path is None or not path.exists():
        return model()
    try:
        return model(**_read_yaml(path))
    except (ValidationError, yaml.YAMLError):
        # 坏配置不能让程序起不来：备份后回退默认
        try:
            shutil.copy2(path, path.with_suffix(path.suffix + ".broken"))
        except Exception:
            pass
        return model()


def save(name: str, cfg: BaseModel) -> Path:
    path = _REGISTRY[name][0]
    _write_yaml(path, cfg.model_dump(mode="json"))
    return path


# ── 便捷访问器（带进程内缓存，热加载时 clear_cache） ────────────

_CACHE: dict[str, BaseModel] = {}


def clear_cache() -> None:
    _CACHE.clear()


def get(name: str) -> BaseModel:
    if name not in _CACHE:
        _CACHE[name] = load(name, _REGISTRY[name][1])
    return _CACHE[name]


def set_(name: str, cfg: BaseModel) -> Path:
    _CACHE[name] = cfg
    return save(name, cfg)


def g() -> GlobalConfig:
    return get("global")  # type: ignore[return-value]


def pet() -> PetProfile:
    return get("pet")  # type: ignore[return-value]


def schedule() -> ScheduleConfig:
    return get("schedule")  # type: ignore[return-value]


def deploy() -> DeployConfig:
    return get("deploy")  # type: ignore[return-value]


def model() -> ModelConfig:
    return get("model")  # type: ignore[return-value]


def modules() -> ModulesConfig:
    return get("modules")  # type: ignore[return-value]


def qq() -> QQConfig:
    return get("qq")  # type: ignore[return-value]


def pricing() -> PricingTable:
    return get("pricing")  # type: ignore[return-value]


def is_initialized() -> bool:
    """是否已完成首次向导（决定启动后跳向导还是跳聊天页）。"""
    return bool(g().wizard.completed) and bool(pet().pet.id)


def ensure_defaults() -> None:
    paths.ensure_dirs()
    for name, (path, m) in _REGISTRY.items():
        if not path.exists():
            save(name, m())
