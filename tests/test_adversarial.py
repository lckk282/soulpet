"""对抗式自检：假设「用户/攻击者/环境会怎么把它弄坏」，逐条验证。

每个用例都对应一个当初真实存在的假设问题：
  · 我把 URL 参数写成攻击载荷会怎样？
  · 我导一份脏数据会怎样？
  · 我的库被断电写坏了还能启动吗？
  · 我开十个标签页会不会把服务拖死？
  · 我传一个 20MB 的 zip 炸弹会怎样？
"""

from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path

DRAFT = {
    "version": 1,
    "ack": {"privacy": True, "cost": True, "risk": True},
    "identity": {"name": "小绫", "role_presets": ["maid"], "asset_source": "builtin"},
    "personality": {
        "sliders": {"clinginess": 50, "verbosity": 50, "snark": 30, "valence": 60, "retention": 60},
        "schedule": {
            "active_start": "09:00",
            "active_hours": 12,
            "proactive": {"quiet_hours": ["23:00", "08:00"]},
        },
    },
    "deploy": {"mode": "local"},
    "model": {"provider": "mock", "model": "mock", "base_url": "http://127.0.0.1:1/v1", "api_key": ""},
    "modules": {"qq": False, "desktop_pet": False},
}


def _ready(client) -> str:
    """保证有宠物可用（本文件可能先于 test_smoke 执行）。"""
    if not client.get("/healthz").json()["initialized"]:
        r = client.post("/api/wizard/commit", json={"draft": DRAFT})
        assert r.status_code == 200, r.text
        return r.json()["pet_id"]
    return client.get("/api/pet").json()["profile"]["pet"]["id"]


# ── 假设一：我把参数写成攻击载荷 ───────────────────────────────


def test_logs_module_cannot_read_outside_logs(client):
    """假设我传 ?module=../../../../Windows/win，能不能读到日志目录外的文件？"""
    r = client.get("/api/status/logs?module=../../../../Windows/win")
    assert r.status_code == 400, r.text
    assert client.get("/api/status/logs?module=backend").status_code == 200


def test_pack_id_rejects_suspicious_names(client):
    """假设我把 pack_id 写成 .hidden / 中文 / 带空格：不能拿来拼路径。"""
    _ready(client)
    for bad in (".hidden", "中文", "a%20b"):
        r = client.get(f"/api/pet/packs/{bad}")
        assert r.status_code in (400, 404), (bad, r.status_code)
    assert client.get("/api/pet/packs/pack_default").status_code == 200

    from fastapi import HTTPException

    from backend.api.pet import _pack_dir

    for bad in ("..", "../config", "a/b", ""):
        try:
            _pack_dir(bad)
            raise AssertionError(f"应当拒绝 {bad!r}")
        except HTTPException:
            pass


def test_zip_slip_is_rejected(tmp_path):
    """假设素材包里塞了 ../../evil.png，解压会不会写到目录外？"""
    from backend.services import asset_pack

    z = tmp_path / "evil.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("../../evil.png", b"x")
    try:
        asset_pack.safe_extract(z, tmp_path / "dest")
        raise AssertionError("应当拒绝路径穿越")
    except ValueError as e:
        assert "非法路径" in str(e)


def test_zip_bomb_is_rejected(tmp_path, monkeypatch):
    """假设我传一个解压后 1GB 的压缩包：不设上限就能把磁盘写满。"""
    from backend.services import asset_pack

    z = tmp_path / "bomb.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("front.png", b"\0" * (8 * 1024 * 1024))
    monkeypatch.setattr(asset_pack, "MAX_UNCOMPRESSED", 1024 * 1024)
    try:
        asset_pack.safe_extract(z, tmp_path / "dest")
        raise AssertionError("应当拒绝超限压缩包")
    except ValueError as e:
        assert "体积过大" in str(e)


def test_zip_rejects_executables(tmp_path):
    """假设我把 .bat 塞进素材包，至少不该被解压落地。"""
    from backend.services import asset_pack

    z = tmp_path / "exe.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("run.bat", b"@echo off")
    try:
        asset_pack.safe_extract(z, tmp_path / "dest")
        raise AssertionError("应当拒绝可执行文件")
    except ValueError as e:
        assert "文件类型" in str(e)


# ── 假设二：我喂脏数据 ─────────────────────────────────────────


def test_import_tolerates_dirty_rows(client):
    """假设导入的 JSON 里 importance 是字符串 / null：不能 500，只能就地纠正或跳过。"""
    _ready(client)
    r = client.post(
        "/api/memory/import",
        json={
            "items": [
                {"content": "主人喜欢下雨天", "importance": 0.9},
                {"content": "脏数据", "importance": "abc"},
                {"content": "空重要度", "importance": None},
            ]
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["imported"] >= 1


def test_import_rejects_non_object_items(client):
    """假设 items 里塞了字符串和 null：整体 422 拒绝，比塞进库更好。"""
    _ready(client)
    r = client.post("/api/memory/import", json={"items": ["这不是对象", None]})
    assert r.status_code == 422


def test_import_is_bounded(client):
    """假设一次导入 10 万条：应当被挡在 5000 条以内。"""
    _ready(client)
    r = client.post("/api/memory/import", json={"items": [{"content": "x"}] * 5001})
    assert r.status_code == 400


def test_blank_message_is_rejected(client):
    """假设我按住空格发一条消息：不该在库里留下空消息。"""
    _ready(client)
    assert client.post("/api/chat", json={"text": "   "}).status_code == 422
    assert client.post("/api/chat", json={"text": "\n\t "}).status_code == 422


def test_limits_are_clamped(client):
    """假设我传 ?limit=999999：不夹紧就会一次把整库捞进内存。"""
    _ready(client)
    r = client.get("/api/memory/timeline?limit=999999")
    assert r.status_code == 200
    assert len(r.json()["items"]) <= 200
    r2 = client.get("/api/chat/history?limit=999999")
    assert r2.status_code == 200 and len(r2.json()["messages"]) <= 400
    assert client.get("/api/memory/search?q=x&topk=99999").status_code == 200
    assert client.get("/api/memory/search?q=x&topk=-1").status_code == 200


def test_like_wildcards_are_escaped(client):
    """假设我搜「%」：不转义就会把整库都匹配出来。"""
    _ready(client)
    total = client.get("/api/memory/stats").json()["data"]["total"]
    hit = client.get("/api/memory/timeline?q=%25").json()
    assert hit["total"] < max(total, 1) or total == 0


def test_search_survives_fts_syntax_error(client):
    """假设我搜「C++」：FTS5 认为这是非法表达式，不能因此什么都搜不到。"""
    _ready(client)
    client.post("/api/memory", json={"content": "主人用 C++ 写后端", "type": "fact", "importance": 0.8})
    items = client.get("/api/memory/search", params={"q": "C++"}).json()["items"]
    assert any("C++" in i["content"] for i in items)


def test_foreign_memory_and_conversation_are_not_accessible(client):
    """假设我拿别的宠物的 id 去改记忆/写会话：必须 404。"""
    pet_id = _ready(client)
    from backend.core import memory_engine
    from backend.db import session
    from backend.models import Conversation

    other = memory_engine.add("pet_other", "别人的秘密", "fact", 0.5, "", "manual")
    assert other is not None
    assert client.put(f"/api/memory/{other.id}", json={"content": "改掉"}).status_code == 404
    assert client.delete(f"/api/memory/{other.id}").status_code == 404

    with session() as s:
        conv = Conversation(pet_id="pet_other", channel="web", scene="private", peer_id="owner")
        s.add(conv)
        s.flush()
        cid = conv.id
    assert client.get(f"/api/chat/history?conv_id={cid}").status_code == 404
    assert client.post("/api/chat", json={"text": "偷偷说话", "conv_id": cid}).status_code == 404
    assert pet_id


# ── 假设三：我拼命戳口令 / 开一堆标签页 ────────────────────────


def test_token_bruteforce_gets_throttled(client, monkeypatch):
    """假设有人在公网实例上暴力猜口令：连续失败后应当被限速。"""
    from backend import auth

    monkeypatch.setenv("SOULPET_ACCESS_TOKEN", "s3cret-token")
    auth._fails.clear()
    try:
        codes = [
            client.get("/api/status", headers={"Authorization": f"Bearer guess{i}"}).status_code for i in range(12)
        ]
        assert 401 in codes and 429 in codes
        # 正确口令也要等封禁过去，这是有意的（否则限速形同虚设）
        assert client.get("/api/status", headers={"Authorization": "Bearer s3cret-token"}).status_code == 429
    finally:
        auth._fails.clear()
        monkeypatch.delenv("SOULPET_ACCESS_TOKEN", raising=False)
    assert client.get("/api/status").status_code == 200


def test_events_stream_is_async_and_alive(client):
    """假设我挂着 SSE 事件流：它必须先吐出 hello，然后持续心跳。"""
    with client.stream("GET", "/api/status/events?max_seconds=10") as resp:
        assert resp.status_code == 200
        head = next(resp.iter_text())
    assert "hello" in head


# ── 假设四：环境坏了 —— 断电把库写坏、目录只读 ─────────────────


def test_broken_database_still_boots(tmp_path):
    """假设断电把 soulpet.db 写成半截垃圾：服务还能起来，坏库被挪到一边。"""
    home = tmp_path / "home"
    (home / "data").mkdir(parents=True)
    (home / "data" / "soulpet.db").write_bytes(b"this is not a sqlite file" * 100)

    env = {**os.environ, "SOULPET_HOME": str(home), "SOULPET_SECRET_BACKEND": "file"}
    root = Path(__file__).resolve().parents[1]
    code = (
        f"import sys;sys.path.insert(0,r'{root}')\n"
        "from fastapi.testclient import TestClient\n"
        "from backend.main import app\n"
        "with TestClient(app) as c:\n"
        "    print('HEALTH', c.get('/healthz').status_code)\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=120)
    assert "HEALTH 200" in out.stdout, out.stdout + out.stderr[-800:]
    assert list((home / "data").glob("soulpet.db.corrupt-*")), "损坏的库应被改名保留"
