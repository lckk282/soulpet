"""SQLite 数据层（SQLAlchemy 2.0）。

生产注意：
  · WAL 模式 + busy_timeout，避免多连接写冲突
  · Uvicorn 必须单 worker，不要用 --workers >1
"""

from __future__ import annotations

import logging
import sqlite3
import time
from contextlib import closing, contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy import exc as sa_exc
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from . import paths

log = logging.getLogger("soulpet.db")


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


def _quarantine_db() -> bool:
    """把损坏的库挪到一边，让程序还能起来。

    断电 / 磁盘写满后 SQLite 可能留下无法打开的库，以前这会直接把启动卡死，
    用户只能自己去翻 data 目录删文件。现在自动改名备份，然后重建空库。
    """
    try:
        engine.dispose()
    except Exception:
        pass
    stamp = time.strftime("%Y%m%d-%H%M%S")
    moved = False
    for suffix in ("", "-wal", "-shm"):
        f = paths.DB_PATH.with_name(paths.DB_PATH.name + suffix)
        if not f.exists():
            continue
        try:
            f.rename(f.with_name(f"{f.name}.corrupt-{stamp}"))
            moved = True
        except Exception as e:
            log.error("无法移走损坏的数据库文件 %s：%s", f, e)
    if moved:
        log.error("数据库文件已损坏，已备份为 *.corrupt-%s 并重建空库（原记忆请从备份恢复）", stamp)
    return moved


def init_db() -> None:
    from . import models  # noqa: F401  导入以注册所有表

    try:
        Base.metadata.create_all(engine)
    except (sqlite3.DatabaseError, sa_exc.DatabaseError) as e:
        # 注意：SQLAlchemy 会把 sqlite3 的错误包成自己的 DatabaseError，
        # 只抓 sqlite3.DatabaseError 是抓不到的 —— 启动照样炸。
        log.error("数据库打开失败（%s），尝试隔离损坏文件后重建", e)
        _quarantine_db()
        Base.metadata.create_all(engine)
    _ensure_fts()


def _ensure_fts() -> None:
    """全文检索表（记忆检索用）。不存在则建，出错不影响主流程。"""
    try:
        with closing(sqlite3.connect(paths.DB_PATH)) as con:
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
