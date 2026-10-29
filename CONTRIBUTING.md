# 参与贡献

谢谢你想让 SoulPet 变得更好。几条约定，照着做就不会踩坑。

## 开发环境

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
ruff check backend launcher tests
```

前端：

```bash
cd frontend && npm install && npm run dev
```

## 分支与提交

- 分支：`feat/xxx`、`fix/xxx`、`docs/xxx`
- 提交信息：`类型: 简述`，如 `feat: 记忆支持置顶`、`fix: 端口占用误判`
- PR 请说明「改了什么 / 为什么 / 怎么验证」

## 代码约定

1. **路径只用 `backend/paths.py`**，不要依赖当前工作目录（打包、开机自启会找不到文件）。
2. **配置改动必须同步 `backend/schemas.py`**，它是配置与 API 的唯一真相来源。
3. **密钥绝不落配置文件、草稿、日志、前端存储**，一律走 `secrets_store`。
4. **SQLite 单 worker**：不要给 uvicorn 加 `--workers > 1`。
5. 新增模块请实现统一接口（`precheck / start / stop / status`），崩了不能带崩主聊天。
6. 涉及第三方协议的功能必须在 UI 与文档里写明风险。

## 测试

- 新增功能请补 `tests/`，测试必须用临时数据目录（`conftest.py` 已通过 `SOULPET_HOME` 隔离）。
- 测试不得访问外网，不得依赖真实 API Key。

## 安全

发现安全问题请私发邮件或在 issue 中选择「Security」，不要公开细节。
