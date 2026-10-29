"""SQLite 数据层（SQLAlchemy 2.0）。

生产注意：
  · WAL 模式 + busy_timeout，避免多连接写冲突
  · Uvicorn 必须单 worker，不要用 --workers >1
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from . import paths


class Base(DeclarativeBase):
    pass


def _make_engine():
    paths.ensure_dirs()
    url = f"sqlite:///{paths.DB_PATH.as_posix()}"
    eng = create_engine(url, future=True, connect_args={"check_same_thread": False, "timeout": 15})

    @event.listens_for(eng, "connect")
    def _set_pragmas(dbapi_conn, _rec):  # pragma: no cover - 依赖驱动
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return eng


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False, future=True)


def init_db() -> None:
    from . import models  # noqa: F401  导入以注册所有表

    Base.metadata.create_all(engine)
    _ensure_fts()


def _ensure_fts() -> None:
    """全文检索表（记忆检索用）。不存在则建，出错不影响主流程。"""
    try:
        with sqlite3.connect(paths.DB_PATH) as con:
            con.execute(
                """CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts
                   USING fts5(memory_id UNINDEXED, content, tokenize='unicode61')"""
            )
    except Exception:
        pass


@contextmanager
def session() -> Session:
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
