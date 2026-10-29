"""密钥存储。

优先级：
  1. 系统钥匙串（Windows 凭据管理器 / macOS Keychain / Linux Secret Service）
  2. data/secrets.enc（AES-GCM，主密码派生；用于无图形环境的 Linux / 容器）
  3. 环境变量 SOULPET_SECRET_<KEY>（容器部署，CI 测试）

配置文件里只存引用字符串（如 keyring://soulpet/llm_api_key），绝不存真值。

环境变量：
  SOULPET_SECRET_BACKEND=file  强制只走加密文件，不碰系统钥匙串（CI / 容器 / 测试）
  SOULPET_MASTER_KEY=<口令>     加密文件后端的主密码
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
from pathlib import Path

from . import paths

SERVICE_NAME = "soulpet"
log = logging.getLogger("soulpet.secrets")

_warned_plaintext = False


class SecretStore:
    def __init__(self, master_key: str | None = None):
        self._backend = None
        self._file_path: Path = paths.SECRETS_PATH
        self._master_key = master_key or os.environ.get("SOULPET_MASTER_KEY", "")
        if os.environ.get("SOULPET_SECRET_BACKEND", "").lower() == "file":
            return
        try:
            import keyring  # noqa: PLC0415

            # 真实探测一次：无可用后端时 keyring 会抛 NoKeyringError
            keyring.get_password(SERVICE_NAME, "__probe__")
            self._backend = keyring
        except Exception:
            self._backend = None

    # ---------- 公开 API ----------

    @property
    def backend_name(self) -> str:
        return "keyring" if self._backend else "file"

    @property
    def plaintext_risk(self) -> bool:
        """没有钥匙串、也没有主密码时，文件后端只能存明文 —— 前端据此提示用户。"""
        return self._backend is None and not self._master_key

    def get(self, key: str) -> str | None:
        env_val = os.environ.get(f"SOULPET_SECRET_{key.upper()}")
        if env_val:
            return env_val
        if self._backend is not None:
            try:
                v = self._backend.get_password(SERVICE_NAME, key)
                if v:
                    return v
            except Exception:
                pass
        return self._file_get(key)

    def set(self, key: str, value: str) -> None:
        if self._backend is not None:
            try:
                self._backend.set_password(SERVICE_NAME, key, value)
                self._file_delete(key)
                return
            except Exception:
                pass
        self._file_set(key, value)

    def delete(self, key: str) -> None:
        if self._backend is not None:
            try:
                self._backend.delete_password(SERVICE_NAME, key)
            except Exception:
                pass
        self._file_delete(key)

    def has(self, key: str) -> bool:
        return bool(self.get(key))

    # ---------- 文件后端 ----------

    def _load_file(self) -> dict:
        if not self._file_path.exists():
            return {}
        try:
            raw = self._file_path.read_bytes()
            data = json.loads(raw.decode("utf-8"))
            if data.get("_plain"):
                return data.get("items", {})
            return json.loads(self._decrypt(data).decode("utf-8"))
        except Exception:
            return {}

    def _save_file(self, items: dict) -> None:
        global _warned_plaintext
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        plain = json.dumps(items, ensure_ascii=False).encode("utf-8")
        try:
            blob = self._encrypt(plain)
        except Exception:
            # 没有 cryptography 或主密码缺失时，退化为明文并显著警告
            if not _warned_plaintext:
                _warned_plaintext = True
                log.warning(
                    "没有可用的加密后端（系统钥匙串不可用且未设置 SOULPET_MASTER_KEY），"
                    "密钥将以明文写入 %s。若在意请设置环境变量 SOULPET_MASTER_KEY 后重启。",
                    self._file_path,
                )
            blob = json.dumps({"_plain": True, "items": items}).encode("utf-8")
        tmp = self._file_path.with_suffix(".tmp")
        tmp.write_bytes(blob)
        tmp.replace(self._file_path)
        try:
            os.chmod(self._file_path, 0o600)
        except Exception:
            pass

    def _file_get(self, key: str) -> str | None:
        return self._load_file().get(key)

    def _file_set(self, key: str, value: str) -> None:
        items = self._load_file()
        items[key] = value
        self._save_file(items)

    def _file_delete(self, key: str) -> None:
        items = self._load_file()
        if key in items:
            items.pop(key)
            self._save_file(items)

    # ---------- 加解密（PBKDF2 + AES-GCM，需要 cryptography） ----------

    def _derive(self, salt: bytes) -> bytes:
        material = (self._master_key or "soulpet-default").encode("utf-8")
        return hashlib.pbkdf2_hmac("sha256", material, salt, 200_000, 32)

    def _encrypt(self, plain: bytes) -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: PLC0415

        if not self._master_key:
            raise RuntimeError("缺少主密码，无法加密落盘")
        salt = secrets.token_bytes(16)
        nonce = secrets.token_bytes(12)
        ct = AESGCM(self._derive(salt)).encrypt(nonce, plain, None)
        return json.dumps(
            {
                "v": 1,
                "salt": base64.b64encode(salt).decode(),
                "nonce": base64.b64encode(nonce).decode(),
                "ct": base64.b64encode(ct).decode(),
            }
        ).encode("utf-8")

    def _decrypt(self, blob: dict) -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: PLC0415

        salt = base64.b64decode(blob["salt"])
        nonce = base64.b64decode(blob["nonce"])
        ct = base64.b64decode(blob["ct"])
        return AESGCM(self._derive(salt)).decrypt(nonce, ct, None)


_store: SecretStore | None = None


def get_store() -> SecretStore:
    global _store
    if _store is None:
        _store = SecretStore()
    return _store
