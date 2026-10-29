"""ORM 模型。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _now() -> datetime:
    return datetime.now()


class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    asset_pack_id: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (Index("idx_conv_peer", "pet_id", "channel", "peer_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_id: Mapped[str] = mapped_column(String(64), default="")
    channel: Mapped[str] = mapped_column(String(16), default="web")
    scene: Mapped[str] = mapped_column(String(16), default="private")
    peer_id: Mapped[str] = mapped_column(String(64), default="owner")
    title: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("idx_msg_conv", "conv_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conv_id: Mapped[int] = mapped_column(Integer, default=0)
    role: Mapped[str] = mapped_column(String(16), default="user")
    content: Mapped[str] = mapped_column(Text, default="")
    emotion: Mapped[str] = mapped_column(String(32), default="")
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Memory(Base):
    __tablename__ = "memories"
    __table_args__ = (Index("idx_mem_pet", "pet_id", "archived", "importance"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_id: Mapped[str] = mapped_column(String(64), default="")
    type: Mapped[str] = mapped_column(String(16), default="fact")
    content: Mapped[str] = mapped_column(Text, default="")
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    emotion: Mapped[str] = mapped_column(String(32), default="")
    source: Mapped[str] = mapped_column(String(16), default="inferred")
    reinforce_count: Mapped[int] = mapped_column(Integer, default=0)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    last_recalled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UsageLog(Base):
    __tablename__ = "usage_logs"
    __table_args__ = (Index("idx_usage_time", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_id: Mapped[str] = mapped_column(String(64), default="")
    provider: Mapped[str] = mapped_column(String(32), default="")
    model: Mapped[str] = mapped_column(String(64), default="")
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_estimated: Mapped[float] = mapped_column(Float, default=0.0)
    is_estimated: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ModuleStatus(Base):
    __tablename__ = "module_status"

    module: Mapped[str] = mapped_column(String(32), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default="stopped")
    last_error: Mapped[str] = mapped_column(Text, default="")
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pid: Mapped[int] = mapped_column(Integer, default=0)


class AssetPack(Base):
    __tablename__ = "asset_packs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    pet_id: Mapped[str] = mapped_column(String(64), default="")
    path: Mapped[str] = mapped_column(String(400), default="")
    report_json: Mapped[str] = mapped_column(Text, default="{}")
    complete: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
