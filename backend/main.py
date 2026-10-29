"""应用装配。"""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager  # noqa: E402
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import paths
from .api import chat, memory, model, modules, pet, status, wizard  # noqa: E402
from .config_store import ensure_defaults, is_initialized  # noqa: E402
from .core import scheduler as sched  # noqa: E402
from .db import init_db  # noqa: E402
from .services import asset_pack, module_manager  # noqa: E402

VERSION = "0.1.0"


def setup_logging(level: str = "INFO") -> None:
    paths.ensure_dirs()
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s")
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    try:
        fh = RotatingFileHandler(
            paths.LOG_DIR / "backend.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except Exception:
        pass

    logging.getLogger("apscheduler").setLevel(logging.WARNING)


def create_app() -> FastAPI:
    paths.ensure_dirs()
    setup_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        ensure_defaults()
        init_db()
        asset_pack.ensure_default_pack()
        try:
            sched.start()
        except Exception:
            pass
        module_manager.start("web_chat")
        try:
            from .config_store import modules as modules_cfg

            cfg = modules_cfg()
            if cfg.qq.enabled:
                module_manager.start("qq")
            if cfg.desktop_pet.enabled:
                module_manager.start("desktop_pet")
        except Exception:
            pass
        logging.getLogger("soulpet").info("SoulPet 已启动，数据目录：%s", paths.HOME)
        yield
        try:
            sched.stop()
        except Exception:
            pass

    app = FastAPI(
        title="SoulPet",
        description="本地优先的私有 AI 宠物",
        version=VERSION,
        docs_url="/api/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1", "http://localhost", "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for r in (wizard.router, chat.router, memory.router, model.router, modules.router, pet.router, status.router):
        app.include_router(r)

    @app.get("/healthz")
    def healthz():
        return {"ok": True, "version": VERSION, "initialized": is_initialized()}

    @app.get("/api/meta")
    def meta():
        from .adapters.llm.registry import load_registry
        from .secrets_store import get_store

        return {
            "ok": True,
            "version": VERSION,
            "initialized": is_initialized(),
            "secret_backend": get_store().backend_name,
            "providers": load_registry(),
            "home": str(paths.HOME),
        }

    # 静态资源：构建过前端就托管 dist，否则走「未构建」提示页
    dist = paths.FRONTEND_DIST
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=str(dist / "assets")), name="assets")

        @app.get("/")
        def index():
            return FileResponse(dist / "index.html")

        @app.get("/{full_path:path}")
        def spa(full_path: str):
            # API 路径不存在时返回 404 JSON，避免前端把首页 HTML 当 JSON 解析、掩盖真实问题
            if full_path.startswith("api/"):
                return JSONResponse({"ok": False, "detail": f"接口不存在: /{full_path}"}, status_code=404)
            # 静态文件优先，其余交给 Vue Router
            root = dist.resolve()
            cand = (dist / full_path).resolve()
            if full_path and cand.is_file() and root in cand.parents:
                return FileResponse(cand)
            return FileResponse(dist / "index.html")
    else:
        @app.get("/")
        def no_frontend():
            return JSONResponse(
                {
                    "ok": False,
                    "message": "前端尚未构建。请执行：cd frontend && npm install && npm run build",
                    "docs": "/api/docs",
                }
            )

    return app


app = create_app()
