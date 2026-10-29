"""QQ 桥接统一抽象与风控闸门。

三种方案（napcat / official / lite）都实现 BridgeAdapter，
上层业务只认 UnifiedMessage，换方案不改聊天逻辑。
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass
class UnifiedMessage:
    platform: str = "qq"
    scheme: str = "napcat"
    scene: str = "private"          # private | group
    group_id: str | None = None
    user_id: str = ""
    msg_id: str = ""
    text: str = ""
    images: list[str] = field(default_factory=list)
    is_at_me: bool = False
    raw: dict = field(default_factory=dict)


@dataclass
class Target:
    scene: str
    id: str


class BridgeAdapter(ABC):
    name: str = "base"

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def events(self) -> AsyncIterator[UnifiedMessage]: ...

    @abstractmethod
    async def send_text(self, target: Target, text: str) -> None: ...


# ── 风控闸门 ────────────────────────────────────────────────────

class RateLimiter:
    """滑动窗口频控：窗口内条数超限即拒绝。"""

    def __init__(self, window_sec: int, max_count: int):
        self.window = window_sec
        self.max = max_count
        self._hits: OrderedDict[float, int] = OrderedDict()

    def allow(self) -> bool:
        now = time.time()
        for t in list(self._hits):
            if now - t > self.window:
                self._hits.pop(t, None)
        total = sum(self._hits.values())
        if total >= self.max:
            return False
        self._hits[now] = self._hits.get(now, 0) + 1
        return True


class CircuitBreaker:
    """连续失败熔断，避免刷日志与加重风控。"""

    def __init__(self, threshold: int = 5, cooldown: int = 900):
        self.threshold = threshold
        self.cooldown = cooldown
        self.fails = 0
        self.opened_at = 0.0

    def ok(self) -> bool:
        if self.opened_at and time.time() - self.opened_at < self.cooldown:
            return False
        if self.opened_at:
            self.opened_at = 0.0
            self.fails = 0
        return True

    def fail(self) -> None:
        self.fails += 1
        if self.fails >= self.threshold:
            self.opened_at = time.time()
            self.fails = 0

    def reset(self) -> None:
        self.fails = 0
        self.opened_at = 0.0


class AutonomyGuard:
    """自主行为闸门：白名单 → 触发判定 → 频控 → 熔断。"""

    def __init__(self, policy: dict):
        self.default_deny = bool(policy.get("default_deny", True))
        self.groups = {str(g.get("id")): g for g in policy.get("groups", [])}
        self.private_enabled = bool(policy.get("private_enabled", True))
        self.private_only_whitelist = bool(policy.get("private_only_whitelist", True))
        self.private_whitelist = {str(x) for x in policy.get("private_whitelist", [])}
        self.group_limiter = RateLimiter(3, 1)      # 群：3 秒 1 条
        self.global_limiter = RateLimiter(3600, 200)  # 全局：1 小时 200 条
        self.breaker = CircuitBreaker()

    def allow(self, msg: UnifiedMessage) -> tuple[bool, str]:
        if not self.breaker.ok():
            return False, "熔断中"
        if msg.scene == "group":
            g = self.groups.get(str(msg.group_id))
            if not g:
                return False, "群不在白名单" if self.default_deny else "未配置该群"
            mode = g.get("mode", "at")
            if mode == "at" and not msg.is_at_me:
                return False, "未 @ 我"
            if mode == "keyword":
                kws = g.get("keywords") or []
                if not any(k in msg.text for k in kws):
                    return False, "未命中关键词"
            if not self.group_limiter.allow():
                return False, "群频控"
        else:
            if not self.private_enabled:
                return False, "私聊已关闭"
            if self.private_only_whitelist and msg.user_id not in self.private_whitelist:
                return False, "私聊不在白名单"
        if not self.global_limiter.allow():
            return False, "全局频控"
        return True, ""
