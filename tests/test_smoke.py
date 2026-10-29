"""端到端冒烟：向导 → 提交 → 聊天 → 记忆 → 状态。

离线体验模式（不填 API Key），无需任何外部服务即可跑通全流程。
"""

DRAFT = {
    "version": 1,
    "ack": {"privacy": True, "cost": True, "risk": True},
    "identity": {
        "name": "小绫",
        "role_presets": ["maid"],
        "role_custom": "说话带点口癖",
        "bio": "有点笨手笨脚但很努力",
        "asset_source": "builtin",
    },
    "personality": {
        "sliders": {"clinginess": 72, "verbosity": 55, "snark": 40, "valence": 80, "retention": 65},
        "tags": ["傲娇"],
        "hard_rules": ["不许提工作压力"],
        "schedule": {
            "timezone": "Asia/Shanghai",
            "active_start": "09:00",
            "active_hours": 12,
            "idle_can_reply": True,
            "proactive": {"enabled": True, "max_per_day": 3, "quiet_hours": ["23:00", "08:00"], "group_enabled": False},
            "auto_browse": {"enabled": False, "sources": [], "max_per_day": 2},
        },
    },
    "deploy": {"mode": "local"},
    "model": {"provider": "mock", "model": "mock", "base_url": "http://127.0.0.1:1/v1", "api_key": ""},
    "modules": {"qq": False, "desktop_pet": True},
    "pet": {"scale": 1.0, "always_on_top": True},
}


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_meta(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    assert "providers" in r.json()


def test_draft_roundtrip(client):
    r = client.post("/api/wizard/draft", json={"draft": {"identity": {"name": "小绫"}}})
    assert r.json()["ok"]
    saved = client.get("/api/wizard/draft").json()["draft"]
    assert saved["draft"]["identity"]["name"] == "小绫"


def test_draft_never_stores_secret(client):
    client.post("/api/wizard/draft", json={"draft": {"model": {"api_key": "sk-secret"}}})
    saved = client.get("/api/wizard/draft").json()["draft"]
    assert saved["draft"]["model"]["api_key"] != "sk-secret"


def test_validate_rejects_incomplete(client):
    r = client.post("/api/wizard/validate", json={"draft": {"identity": {"name": "x"}}})
    body = r.json()
    assert body["ok"] is False
    assert body["errors"]


def test_commit_and_chat(client):
    r = client.post("/api/wizard/commit", json={"draft": DRAFT})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] and data["pet_id"].startswith("pet_")

    # 种子记忆存在
    mem = client.get("/api/memory/timeline").json()
    assert mem["total"] >= 1
    assert "小绫" in mem["items"][-1]["content"]

    # 档案与派生参数
    prof = client.get("/api/pet").json()["profile"]
    assert prof["pet"]["name"] == "小绫"
    assert 0 < prof["personality"]["derived"]["temperature"] <= 0.95

    # 聊天（SSE）
    with client.stream("POST", "/api/chat", json={"text": "你好呀"}) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())
    assert "delta" in body and "done" in body

    # 消息落库
    hist = client.get("/api/chat/history").json()
    assert len(hist["messages"]) >= 2


def test_memory_manual(client):
    r = client.post("/api/memory", json={"content": "主人怕黑", "type": "preference", "importance": 0.9})
    assert r.json()["ok"]
    tl = client.get("/api/memory/timeline?q=怕黑").json()
    assert tl["total"] >= 1
    stats = client.get("/api/memory/stats").json()["data"]
    assert stats["total"] >= 2


def test_asset_pack_default(client):
    packs = client.get("/api/pet/packs").json()["items"]
    assert any(p["id"] == "pack_default" for p in packs)
    detail = client.get("/api/pet/packs/pack_default").json()
    assert detail["report"]["complete"] is True


def test_status_and_modules(client):
    st = client.get("/api/status").json()
    assert st["state"] in ("ACTIVE", "IDLE", "SAVING")
    assert "desktop_pet" in st["modules"]
    mods = client.post("/api/modules/desktop_pet/toggle", json={"enabled": False}).json()
    assert mods["ok"]


def test_usage_endpoint(client):
    u = client.get("/api/status/usage").json()
    assert u["ok"]
    assert "today" in u["data"]


def test_personality_affects_temperature(client):
    """粘人/吐槽拉满时的温度必须高于全零，且不超过 0.95。"""
    from backend.core.prompt_builder import map_sampling

    low = map_sampling({"clinginess": 0, "verbosity": 0, "snark": 0, "valence": 0, "retention": 0})
    high = map_sampling({"clinginess": 100, "verbosity": 100, "snark": 100, "valence": 100, "retention": 100})
    assert high["temperature"] > low["temperature"]
    assert high["temperature"] <= 0.95
    assert high["max_tokens"] > low["max_tokens"]
