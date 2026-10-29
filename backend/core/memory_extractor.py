"""记忆抽取：从一轮对话里挑出值得记住的内容。

默认走规则抽取（零成本、零延迟）；开启 LLM 抽取后（配置 memory_extract=llm）
再调用模型做结构化抽取，失败自动回退规则。
"""
from __future__ import annotations

import re

PREF_PAT = re.compile(
    r"(我(?:很|挺|最|不|不太|特别)?(?:喜欢|讨厌|害怕|想|希望|习惯|需要))(.{1,30})"
)
FACT_PAT = re.compile(
    r"(我(?:叫|是|住在|在|今年|刚|已经|的.{1,6}是))(.{1,30})"
)
NEGatives = ("吗", "？", "?")


def rule_extract(user_text: str, reply: str = "") -> list[dict]:
    """规则抽取：抓偏好句与事实句。宁可少记，不要乱记。"""
    out: list[dict] = []
    text = (user_text or "").strip()
    if len(text) < 4 or len(text) > 500:
        return out

    for m in PREF_PAT.finditer(text):
        frag = (m.group(1) + m.group(2)).strip(" ，。,.!！")
        if len(frag) < 4 or frag.endswith(NEGatives):
            continue
        out.append({"type": "preference", "content": frag, "importance": 0.7, "source": "user_stated"})

    for m in FACT_PAT.finditer(text):
        frag = (m.group(1) + m.group(2)).strip(" ，。,.!！")
        if len(frag) < 4:
            continue
        out.append({"type": "fact", "content": frag, "importance": 0.6, "source": "user_stated"})

    # 去重
    seen, uniq = set(), []
    for it in out:
        if it["content"] in seen:
            continue
        seen.add(it["content"])
        uniq.append(it)
    return uniq[:3]


EXTRACT_PROMPT = """从下面这段对话里抽取值得长期记住的信息，只输出 JSON，不要任何解释。
格式：{"events":[{"type":"fact|emotion|preference","text":"...","importance":0.0~1.0,"emo":"happy|shy|sad|neutral"}]}
规则：只记关于「用户」的稳定事实、偏好与情绪；不记闲聊；没有就输出 {"events":[]}。

用户：{user}
宠物：{reply}
"""


def llm_extract(user_text: str, reply: str, llm) -> list[dict] | None:
    import json

    try:
        raw = llm.chat(
            [
                {"role": "system", "content": "你是记忆抽取器，只输出 JSON。"},
                {
                    "role": "user",
                    "content": EXTRACT_PROMPT.format(user=user_text[:500], reply=reply[:500]),
                },
            ],
            temperature=0.2,
            max_tokens=300,
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`").replace("json", "", 1).strip()
        data = json.loads(raw)
        events = data.get("events") or []
        out = []
        for e in events[:5]:
            t = e.get("text", "").strip()
            if not t:
                continue
            out.append(
                {
                    "type": e.get("type", "fact") if e.get("type") in ("fact", "emotion", "preference") else "fact",
                    "content": t[:200],
                    "importance": float(e.get("importance", 0.6) or 0.6),
                    "emotion": e.get("emo", ""),
                    "source": "inferred",
                }
            )
        return out
    except Exception:
        return None
