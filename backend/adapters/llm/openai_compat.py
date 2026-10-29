"""LLM 适配器：OpenAI 兼容协议。

只依赖 httpx。所有"OpenAI 兼容"厂商（含自建 vLLM / Ollama / 聚合网关）都能直接用。
错误统一分类为：auth / rate / timeout / net / bad，前端可翻译成人话。
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from ...schemas import ModelConfig

TIMEOUT_DEFAULT = 60


class LLMError(Exception):
    def __init__(self, kind: str, detail: str, status: int = 0):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail
        self.status = status


HINTS = {
    "auth": "密钥不对或已失效，检查 API Key 是否复制完整",
    "rate": "被限流或额度不足，检查账户余额与速率限制",
    "timeout": "请求超时，检查网络或把超时时间调大",
    "net": "连不上接口地址，检查网络、代理或 base_url 是否正确",
    "bad": "接口返回异常，检查 base_url 和模型名是否匹配",
    "model": "模型名不存在或该账号无权限",
}


def normalize_base_url(base: str) -> list[str]:
    """各厂商 base_url 后缀不一致（有人要 /v1 有人不要），返回候选列表逐个试。"""
    base = (base or "").strip().rstrip("/")
    if not base:
        return []
    cands = [base]
    if not base.endswith("/v1"):
        cands.append(base + "/v1")
    if base.endswith("/v1"):
        cands.append(base[: -len("/v1")])
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


class OpenAICompatLLM:
    def __init__(self, cfg: ModelConfig, api_key: str, timeout: int | None = None):
        self.cfg = cfg
        self.api_key = api_key
        self.timeout = timeout or cfg.advanced.timeout_sec or TIMEOUT_DEFAULT
        self._client = httpx.Client(timeout=self.timeout, follow_redirects=True)
        self.base = cfg.base_url.rstrip("/")

    # ── 连通测试 ──────────────────────────────────────────────
    def ping(self) -> dict:
        """发一条极短请求验证连通性；自动尝试 base_url 的多种拼法。"""
        last_err: LLMError | None = None
        for base in normalize_base_url(self.cfg.base_url):
            try:
                r = self._client.post(
                    base + "/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": self.cfg.model,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 8,
                        "stream": False,
                    },
                )
            except httpx.TimeoutException as e:
                last_err = LLMError("timeout", str(e))
                continue
            except httpx.HTTPError as e:
                last_err = LLMError("net", str(e))
                continue

            if r.status_code in (401, 403):
                last_err = LLMError("auth", r.text[:200], r.status_code)
                continue
            if r.status_code == 429:
                last_err = LLMError("rate", r.text[:200], r.status_code)
                continue
            if r.status_code == 404:
                last_err = LLMError("bad", f"404 {r.text[:160]}", 404)
                continue
            if r.status_code >= 500:
                last_err = LLMError("bad", f"{r.status_code} {r.text[:160]}", r.status_code)
                continue
            if r.status_code >= 400:
                txt = r.text[:200]
                kind = "model" if "model" in txt.lower() else "bad"
                last_err = LLMError(kind, txt, r.status_code)
                continue

            self.base = base  # 记住可用拼法
            try:
                data = r.json()
                real = (data.get("model") or self.cfg.model) if isinstance(data, dict) else self.cfg.model
            except Exception:
                real = self.cfg.model
            return {"ok": True, "base_url": base, "model": str(real), "latency_ms": int(r.elapsed.total_seconds() * 1000)}

        raise last_err or LLMError("net", "无法连接")

    # ── 对话 ──────────────────────────────────────────────────
    def chat(self, messages: list[dict], **override) -> str:
        return "".join(self.stream(messages, **override))

    def stream(self, messages: list[dict], **override) -> Iterator[str]:
        payload: dict[str, Any] = {
            "model": override.get("model") or self.cfg.model,
            "messages": messages,
            "temperature": override.get("temperature", 0.75),
            "top_p": override.get("top_p", 0.9),
            "max_tokens": override.get("max_tokens", 500),
            "frequency_penalty": override.get("frequency_penalty", 0.3),
            "presence_penalty": override.get("presence_penalty", 0.2),
            "stream": True,
        }
        url = self.base + "/chat/completions"
        try:
            with self._client.stream("POST", url, headers=self._headers(), json=payload) as r:
                if r.status_code >= 400:
                    body = r.read().decode("utf-8", "ignore")[:200]
                    kind = "auth" if r.status_code in (401, 403) else (
                        "rate" if r.status_code == 429 else "bad"
                    )
                    raise LLMError(kind, body, r.status_code)
                for line in r.iter_lines():
                    if not line:
                        continue
                    if isinstance(line, bytes):
                        line = line.decode("utf-8", "ignore")
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        import json

                        obj = json.loads(data)
                        delta = obj["choices"][0].get("delta", {})
                        piece = delta.get("content")
                        if piece:
                            yield piece
                    except Exception:
                        continue
        except httpx.TimeoutException as e:
            raise LLMError("timeout", str(e)) from e
        except httpx.HTTPError as e:
            raise LLMError("net", str(e)) from e

    # ── 向量（可选） ───────────────────────────────────────────
    def embed(self, texts: list[str]) -> list[list[float]] | None:
        if not self.cfg.embedding_enabled:
            return None
        try:
            r = self._client.post(
                self.base + "/embeddings",
                headers=self._headers(),
                json={"model": self.cfg.embedding_model or "text-embedding-3-small", "input": texts},
            )
            if r.status_code >= 400:
                return None
            data = r.json().get("data", [])
            return [d.get("embedding", []) for d in data]
        except Exception:
            return None

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass
