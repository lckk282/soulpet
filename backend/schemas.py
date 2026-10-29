"""配置与 API 的数据模型（Pydantic v2）。

这里是整个项目的地基：
  · config/*.yaml 的结构由本文件的 Config* 模型定义
  · 前端向导表单由本文件的 *Form 模型定义（前端校验规则与之对应）
  · 后端 API 的请求/响应同样由本文件定义
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class _Base(BaseModel):
    model_config = {"extra": "ignore", "populate_by_name": True}


# ─────────────────────────────────────────────────────────────
# 一、配置文件模型（落盘到 config/*.yaml）
# ─────────────────────────────────────────────────────────────


class ServerConfig(_Base):
    host: str = "127.0.0.1"
    port: int = 8787
    pet_ws_port: int = 8788
    auth_required: bool = False
    auto_open_browser: bool = True


class AckRecord(_Base):
    privacy: bool = False
    cost: bool = False
    risk: bool = False
    at: str | None = None


class WizardState(_Base):
    completed: bool = False
    version: int = 1
    ack: AckRecord = Field(default_factory=AckRecord)


class GlobalConfig(_Base):
    version: int = 1
    instance_id: str = ""
    installed_at: str = ""
    wizard: WizardState = Field(default_factory=WizardState)
    server: ServerConfig = Field(default_factory=ServerConfig)
    log_level: str = "INFO"
    secret_backend: str = "auto"


class PetIdentity(_Base):
    id: str = ""
    name: str = "小绫"
    role_presets: list[str] = Field(default_factory=list)
    role_custom: str = ""
    bio: str = ""
    avatar_pack_id: str = ""
    avatar_slot: str = "front"


class Sliders(_Base):
    """五维性格滑块，取值 0~100。"""

    clinginess: int = 50
    verbosity: int = 50
    snark: int = 30
    valence: int = 60
    retention: int = 60

    @field_validator("*")
    @classmethod
    def _clamp(cls, v: int) -> int:
        return max(0, min(100, int(v)))


class DerivedParams(_Base):
    """由滑块派生、运行时直接使用的参数（提交时计算并固化）。"""

    temperature: float = 0.75
    top_p: float = 0.9
    max_tokens: int = 500
    proactive_base_per_day: int = 3
    memory_topk: int = 7
    memory_write_threshold: float = 0.5


class Personality(_Base):
    sliders: Sliders = Field(default_factory=Sliders)
    tags: list[str] = Field(default_factory=list)
    hard_rules: list[str] = Field(default_factory=list)
    derived: DerivedParams = Field(default_factory=DerivedParams)


class PetProfile(_Base):
    pet: PetIdentity = Field(default_factory=PetIdentity)
    personality: Personality = Field(default_factory=Personality)


class ProactiveConfig(_Base):
    enabled: bool = True
    max_per_day: int = 3
    quiet_hours: list[str] = Field(default_factory=lambda: ["23:00", "08:00"])
    group_enabled: bool = False


class AutoBrowseConfig(_Base):
    enabled: bool = False
    sources: list[dict[str, str]] = Field(default_factory=list)
    max_per_day: int = 2


class ScheduleConfig(_Base):
    timezone: str = "Asia/Shanghai"
    active_start: str = "09:00"
    active_hours: int = 12
    idle_can_reply: bool = True
    proactive: ProactiveConfig = Field(default_factory=ProactiveConfig)
    auto_browse: AutoBrowseConfig = Field(default_factory=AutoBrowseConfig)


class CloudDeploy(_Base):
    host: str = ""
    ssh_port: int = 22
    user: str = "root"
    auth_type: Literal["password", "key"] = "key"
    key_path: str = ""
    remote_dir: str = "/opt/soulpet"
    public_port: int = 443
    domain: str = ""
    https: Literal["none", "letsencrypt", "selfsigned"] = "none"
    email: str = ""


class DeployConfig(_Base):
    mode: Literal["local", "cloud"] = "local"
    cloud: CloudDeploy = Field(default_factory=CloudDeploy)


class BudgetConfig(_Base):
    daily_warn_cny: float = 5.0
    monthly_cap_cny: float = 50.0
    auto_idle_on_cap: bool = True


class Pricing(_Base):
    input_per_mtokens: float = 0.0
    output_per_mtokens: float = 0.0
    currency: str = "CNY"
    source: Literal["user", "table", "unknown"] = "unknown"


class AdvancedModel(_Base):
    temperature_delta: float = 0.0
    context_turns: int = 20
    stream: bool = True
    retries: int = 2
    timeout_sec: int = 60


class ModelConfig(_Base):
    provider: str = "custom"
    model: str = ""
    base_url: str = ""
    api_key_ref: str = "keyring://soulpet/llm_api_key"
    pricing: Pricing = Field(default_factory=Pricing)
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    advanced: AdvancedModel = Field(default_factory=AdvancedModel)
    embedding_enabled: bool = False
    embedding_model: str = ""


class QQGroupPolicy(_Base):
    id: str = ""
    mode: Literal["at", "keyword", "all"] = "at"
    keywords: list[str] = Field(default_factory=list)


class QQPolicy(_Base):
    default_deny: bool = True
    groups: list[QQGroupPolicy] = Field(default_factory=list)
    private_enabled: bool = True
    private_only_whitelist: bool = True
    private_whitelist: list[str] = Field(default_factory=list)


class QQConfig(_Base):
    enabled: bool = False
    scheme: Literal["napcat", "official", "lite"] | None = None
    ws_url: str = "ws://127.0.0.1:3001"
    token_ref: str = "keyring://soulpet/qq_token"
    app_id: str = ""
    app_secret_ref: str = "keyring://soulpet/qq_app_secret"
    policy: QQPolicy = Field(default_factory=QQPolicy)
    risk_accepted: bool = False
    risk_accepted_at: str | None = None


class DesktopPetConfig(_Base):
    enabled: bool = False
    pack_id: str = ""
    scale: float = 1.0
    always_on_top: bool = True
    click_through: bool = False
    opacity: int = 100


class ModulesConfig(_Base):
    qq: QQConfig = Field(default_factory=QQConfig)
    desktop_pet: DesktopPetConfig = Field(default_factory=DesktopPetConfig)
    web_chat: bool = True


class PricingTable(_Base):
    """单价表：单位「元 / 百万 tokens」。留空由用户按厂商公告填写。"""

    currency: str = "CNY"
    updated_at: str = ""
    note: str = "价格以厂商官方公告为准；未填写时费用统计不可用。"
    models: dict[str, dict[str, float]] = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────
# 二、向导表单模型（前端提交 / 后端二次校验）
# ─────────────────────────────────────────────────────────────


class AckForm(_Base):
    privacy: bool
    cost: bool
    risk: bool


class IdentityForm(_Base):
    name: str = Field(min_length=1, max_length=16)
    role_presets: list[str] = Field(default_factory=list)
    role_custom: str = ""
    bio: str = ""
    asset_pack_id: str = ""
    asset_source: Literal["generate", "upload", "builtin", "none"] = "none"

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("名字不能为空")
        if v.lower() in {"system", "admin", "root"}:
            raise ValueError("这个名字被系统保留，换一个吧")
        return v


class PersonalityForm(_Base):
    sliders: Sliders = Field(default_factory=Sliders)
    tags: list[str] = Field(default_factory=list)
    hard_rules: list[str] = Field(default_factory=list)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)


class DeployForm(_Base):
    mode: Literal["local", "cloud"] = "local"
    cloud: CloudDeploy | None = None


class ModelForm(_Base):
    provider: str = "custom"
    model: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    api_key: str = ""  # 仅在提交时传递一次，绝不落盘到配置/草稿文件
    pricing: Pricing = Field(default_factory=Pricing)
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    advanced: AdvancedModel = Field(default_factory=AdvancedModel)
    embedding_enabled: bool = False
    embedding_model: str = ""


class ModulesForm(_Base):
    qq: bool = False
    desktop_pet: bool = False


class QQForm(_Base):
    scheme: Literal["napcat", "official", "lite"] = "napcat"
    ws_url: str = ""
    token: str = ""
    app_id: str = ""
    app_secret: str = ""
    groups: list[QQGroupPolicy] = Field(default_factory=list)
    private_enabled: bool = True
    private_whitelist: list[str] = Field(default_factory=list)
    risk_accepted: bool = False


class PetAssetForm(_Base):
    pack_id: str = ""
    scale: float = 1.0
    always_on_top: bool = True
    click_through: bool = False
    opacity: int = 100


class WizardDraft(_Base):
    version: int = 1
    ack: AckForm | None = None
    identity: IdentityForm | None = None
    personality: PersonalityForm | None = None
    deploy: DeployForm | None = None
    model: ModelForm | None = None
    modules: ModulesForm | None = None
    qq: QQForm | None = None
    pet: PetAssetForm | None = None


# ─────────────────────────────────────────────────────────────
# 三、API 小模型
# ─────────────────────────────────────────────────────────────


class Ok(BaseModel):
    ok: bool = True
    message: str = ""


class ItemOut(BaseModel):
    ok: bool = True
    data: dict[str, Any] | list[Any] | None = None
    warnings: list[str] = Field(default_factory=list)


class ChatRequest(_Base):
    text: str = Field(min_length=1, max_length=4000)
    conv_id: int | None = None
    stream: bool = True


class MemoryOut(BaseModel):
    id: int
    type: str
    content: str
    importance: float
    emotion: str | None = None
    source: str
    reinforce_count: int
    pinned: bool
    created_at: str


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
