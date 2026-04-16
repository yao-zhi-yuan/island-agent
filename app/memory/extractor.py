from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ProfileCandidate:
    category: str
    memory_key: str
    memory_value: str
    content: str
    confidence: float


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _looks_like_question(text: str) -> bool:
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    if "?" in lowered or "？" in lowered:
        return True
    question_tokens = ("什么", "怎么", "吗", "为何", "为什么", "哪种", "哪个", "where", "what", "why", "how")
    return any(token in lowered for token in question_tokens)


def _hash_key(prefix: str, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _extract_candidates_from_text(text: str) -> list[ProfileCandidate]:
    text = _normalize_whitespace(text)
    lowered = text.lower()
    if not text:
        return []

    candidates: list[ProfileCandidate] = []

    if re.search(r"(以后|默认|请|都用).*(中文|汉语|chinese)", text, re.I):
        candidates.append(
            ProfileCandidate(
                category="preference",
                memory_key="response_language",
                memory_value="zh-CN",
                content="用户偏好：默认使用中文回复。",
                confidence=0.95,
            )
        )
    if re.search(r"(以后|默认|请|都用).*(英文|英语|english)", text, re.I):
        candidates.append(
            ProfileCandidate(
                category="preference",
                memory_key="response_language",
                memory_value="en-US",
                content="用户偏好：默认使用英文回复。",
                confidence=0.95,
            )
        )
    if re.search(r"(简洁|简短|精炼|concise|brief)", lowered, re.I):
        candidates.append(
            ProfileCandidate(
                category="preference",
                memory_key="response_style",
                memory_value="concise",
                content="用户偏好：回答尽量简洁，优先给结论。",
                confidence=0.78,
            )
        )
    if re.search(r"(详细|展开|一步一步|step by step|详细解释)", lowered, re.I):
        candidates.append(
            ProfileCandidate(
                category="preference",
                memory_key="response_style",
                memory_value="detailed",
                content="用户偏好：回答时提供更详细、分步骤的说明。",
                confidence=0.78,
            )
        )
    if re.search(r"(代码优先|直接给代码|show me the code|code first)", lowered, re.I):
        candidates.append(
            ProfileCandidate(
                category="preference",
                memory_key="response_format",
                memory_value="code_first",
                content="用户偏好：优先给出可执行代码，再补充说明。",
                confidence=0.82,
            )
        )
    if re.search(r"(macos|mac|苹果电脑)", lowered, re.I):
        candidates.append(
            ProfileCandidate(
                category="environment",
                memory_key="primary_os",
                memory_value="macos",
                content="用户常用环境：macOS。",
                confidence=0.72,
            )
        )
    if re.search(r"(windows|win11|win10)", lowered, re.I):
        candidates.append(
            ProfileCandidate(
                category="environment",
                memory_key="primary_os",
                memory_value="windows",
                content="用户常用环境：Windows。",
                confidence=0.72,
            )
        )
    if re.search(r"(linux|ubuntu|debian|centos|alpine)", lowered, re.I):
        candidates.append(
            ProfileCandidate(
                category="environment",
                memory_key="primary_os",
                memory_value="linux",
                content="用户常用环境：Linux。",
                confidence=0.72,
            )
        )

    explicit = ""
    for marker in ("请记住", "记住", "remember that", "以后默认", "默认情况下"):
        idx = lowered.find(marker.lower())
        if idx >= 0:
            explicit = text[idx:]
            break
    if explicit:
        explicit = explicit[:160]
        candidates.append(
            ProfileCandidate(
                category="explicit",
                memory_key=_hash_key("explicit", explicit),
                memory_value=explicit,
                content=f"用户显式要求：{explicit}",
                confidence=0.88,
            )
        )
    elif (not _looks_like_question(text)) and re.search(r"(我喜欢|我偏好|我习惯|我通常|我一般|prefer|usually)", lowered, re.I):
        snippet = text[:160]
        candidates.append(
            ProfileCandidate(
                category="preference_note",
                memory_key=_hash_key("pref_note", snippet),
                memory_value=snippet,
                content=f"用户偏好补充：{snippet}",
                confidence=0.66,
            )
        )

    deduped: list[ProfileCandidate] = []
    seen: set[tuple[str, str, str]] = set()
    for item in candidates:
        key = (item.category, item.memory_key, item.memory_value)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def extract_profile_candidates(user_message: str) -> list[ProfileCandidate]:
    text = _normalize_whitespace(user_message)
    if not text:
        return []
    if _looks_like_question(text) and not re.search(r"(请记住|记住|以后默认|默认情况下)", text, re.I):
        return []
    return _extract_candidates_from_text(text)


def extract_profile_candidates_from_facts(facts: list[str]) -> list[ProfileCandidate]:
    deduped: list[ProfileCandidate] = []
    seen: set[tuple[str, str, str]] = set()
    for fact in facts:
        for item in _extract_candidates_from_text(fact):
            key = (item.category, item.memory_key, item.memory_value)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
    return deduped


def build_episode_summary(user_message: str, assistant_message: str) -> str | None:
    user_text = _normalize_whitespace(user_message)
    assistant_text = _normalize_whitespace(assistant_message)
    if len(user_text) < 8 or len(assistant_text) < 80:
        return None
    if user_text.startswith(("记住", "请记住", "remember")) and len(assistant_text) < 140:
        return None

    user_preview = user_text[:120]
    assistant_preview = assistant_text[:220]
    return f"用户问题：{user_preview}\n处理结论：{assistant_preview}"
