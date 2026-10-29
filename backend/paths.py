"""路径解析。

所有模块必须从这里取路径，禁止依赖当前工作目录（cwd），
否则打包 / 开机自启 / 从别的目录启动时都会找不到文件。

环境变量：
  SOULPET_HOME  数据根目录（配置、数据库、日志、素材），默认等于仓库根目录
"""
from __future__ import annotations

import os
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]  # <repo>/

_home = os.environ.get("SOULPET_HOME")
HOME = Path(_home).resolve() if _home else APP_ROOT

CONFIG_DIR = HOME / "config"
DATA_DIR = HOME / "data"
LOG_DIR = DATA_DIR / "logs"
MEMORY_DIR = DATA_DIR / "memory"
ASSET_DIR = DATA_DIR / "assets"
BACKUP_DIR = DATA_DIR / "backups"

DB_PATH = DATA_DIR / "soulpet.db"
DRAFT_PATH = DATA_DIR / "wizard_draft.json"
SECRETS_PATH = DATA_DIR / "secrets.enc"
PID_PATH = DATA_DIR / "backend.pid"

GLOBAL_CONFIG = CONFIG_DIR / "global.yaml"
PET_PROFILE = CONFIG_DIR / "pet.profile.yaml"
SCHEDULE_CONFIG = CONFIG_DIR / "schedule.yaml"
DEPLOY_CONFIG = CONFIG_DIR / "deploy.yaml"
MODEL_CONFIG = CONFIG_DIR / "model.yaml"
MODULES_CONFIG = CONFIG_DIR / "modules.yaml"
QQ_CONFIG = CONFIG_DIR / "qq.yaml"
PRICING_CONFIG = CONFIG_DIR / "pricing.yaml"
MODEL_REGISTRY = CONFIG_DIR / "model_registry.yaml"

FRONTEND_DIR = APP_ROOT / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"


def ensure_dirs() -> None:
    """确保运行时目录存在。启动时调用一次。"""
    for d in (CONFIG_DIR, DATA_DIR, LOG_DIR, MEMORY_DIR, ASSET_DIR, BACKUP_DIR):
        d.mkdir(parents=True, exist_ok=True)


def to_display(p: Path) -> str:
    """把绝对路径转成对用户友好的相对显示（用于日志与前端展示）。"""
    try:
        return str(p.resolve().relative_to(HOME))
    except Exception:
        return str(p)
