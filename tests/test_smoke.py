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
    # 密钥字段应被整条丢弃，而不是留一个 "***" 占位符（占位符被读回提交就成了假密钥）
    assert "api_key" not in saved["draft"]["model"]
    assert "sk-secret" not in str(saved)


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


def test_cors_rejects_foreign_origin(client):
    """任意网站不能读本机 API：非白名单 Origin 不得拿到 Access-Control-Allow-Origin。"""
    evil = {"Origin": "https://evil.example.com"}
    r = client.get("/api/status", headers=evil)
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}
    ok = {"Origin": "http://127.0.0.1:5173"}
    r2 = client.get("/api/status", headers=ok)
    assert r2.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


def test_backup_is_readable_snapshot(client):
    """WAL 模式下直接 copy .db 会漏数据；备份出来的库必须能独立打开且含最新数据。"""
    import sqlite3
    import zipfile

    path = client.post("/api/status/backup").json()["path"]
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        assert any(n.endswith("soulpet.db") for n in names), names
        with zf.open([n for n in names if n.endswith("soulpet.db")][0]) as f:
            tmp = path + ".tmp.db"
            with open(tmp, "wb") as out:
                out.write(f.read())
    con = sqlite3.connect(tmp)
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"pets", "memories", "messages"} <= tables
        assert con.execute("SELECT COUNT(*) FROM memories").fetchone()[0] >= 1
    finally:
        con.close()


def test_logs_lines_is_capped(client):
    """?lines= 不能无上限，避免一次请求把整份日志读进内存。"""
    body = client.get("/api/status/logs?lines=99999999").json()
    assert len(body["lines"]) <= 5000


def test_delete_missing_conversation_404(client):
    assert client.delete("/api/chat/999999").status_code == 404


def test_access_token_guard(client, monkeypatch):
    """云服部署时口令必须真的拦得住，否则 README 里的安全承诺就是空话。"""
    monkeypatch.setenv("SOULPET_ACCESS_TOKEN", "s3cret-token")
    try:
        r = client.get("/api/memory/timeline")
        assert r.status_code == 401
        assert r.json().get("need_token") is True
        # 健康检查要放行，否则容器探针会把服务判死
        assert client.get("/healthz").status_code == 200
        # Bearer 与 ?token= 两种方式都要能用
        ok = client.get("/api/memory/timeline", headers={"Authorization": "Bearer s3cret-token"})
        assert ok.status_code == 200
        ok2 = client.get("/api/status?token=s3cret-token", follow_redirects=False)
        assert ok2.status_code == 302
        assert "token=" not in ok2.headers["location"]
        # 错口令不能过
        assert client.get("/api/status", headers={"Authorization": "Bearer wrong"}).status_code == 401
    finally:
        monkeypatch.delenv("SOULPET_ACCESS_TOKEN", raising=False)
    # 关掉之后立刻恢复免密，本地使用不受影响
    assert client.get("/api/status").status_code == 200


def test_reset_really_wipes_everything(client):
    """「恢复出厂」必须真的把记忆清掉，而不是只删配置文件。

    这个用例放在文件最后：它会把数据清空，后面的用例就没东西可测了。
    """
    client.post("/api/memory", json={"content": "待清除的记忆", "type": "event", "importance": 0.5})
    assert client.get("/api/memory/stats").json()["data"]["total"] >= 1

    r = client.post("/api/wizard/reset").json()
    assert r["ok"] is True
    assert r["restart_required"] is True
    assert r["backup"], "重置前必须先自动备份"

    assert client.get("/api/pet").json()["profile"]["pet"]["id"] == ""
    # 宠物没了，记忆接口应当回到「还没有创建宠物」的状态
    assert client.get("/api/memory/stats").status_code == 409
    # 不重启也不能报「no such table」
    assert client.get("/api/status").status_code == 200
