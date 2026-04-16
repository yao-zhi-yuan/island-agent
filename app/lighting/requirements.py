from __future__ import annotations

import re
from typing import Any


# Step 2A 的需求结构化保持“规则优先”。
# 低风险字段用关键词做受控推断；尺寸、层高、预算等高风险字段只在用户明确给出时写入。
_SPACE_KEYWORDS = [
    ("bedroom", ("卧室", "主卧", "次卧", "睡房", "bedroom")),
    ("living_room", ("客厅", "起居室", "living room")),
    ("dining_room", ("餐厅", "饭厅", "dining room")),
    ("study", ("书房", "学习区", "study")),
    ("office", ("办公室", "办公区", "office")),
]

_STYLE_KEYWORDS = [
    ("warm", ("温馨", "暖", "柔和", "舒适", "warm")),
    ("modern", ("现代", "现代风格", "modern")),
    ("minimal", ("简约", "极简", "简单", "minimal")),
    ("bright", ("明亮", "通透", "亮堂", "bright")),
]

_LIGHTING_INTENT_KEYWORDS = ("照明", "灯光", "灯具", "布灯", "lighting", "light")

# 判断一段文本里是否包含任意一个关键词（不区分大小写）
def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)

# 根据文本内容，自动匹配出对应的分类 / 标签 / 值（关键词映射匹配）
def _match_keyword_value(text: str, mapping: list[tuple[str, tuple[str, ...]]]) -> str | None:
    for value, keywords in mapping:
        if _contains_any(text, keywords):
            return value
    return None


def _extract_dimensions(text: str) -> dict[str, Any]:
    """只解析用户明确说出的尺寸或面积，不做默认值。"""

    dimensions: dict[str, Any] = {}

    size_match = re.search(
        r"(?P<width>\d+(?:\.\d+)?)\s*(?:m|米)?\s*[xX×*]\s*(?P<length>\d+(?:\.\d+)?)\s*(?:m|米)?",
        text,
    )
    if size_match:
        dimensions["width"] = float(size_match.group("width"))
        dimensions["length"] = float(size_match.group("length"))
        dimensions["unit"] = "m"

    area_match = re.search(r"(?P<area>\d+(?:\.\d+)?)\s*(?:平米|平方米|㎡|m2|m²)", text, re.IGNORECASE)
    if area_match:
        dimensions["area"] = float(area_match.group("area"))
        dimensions.setdefault("unit", "m")

    return dimensions


def _extract_ceiling_height(text: str) -> float | None:
    match = re.search(r"(?:层高|吊顶后高度|净高|高)\s*(?P<height>\d+(?:\.\d+)?)\s*(?:m|米)?", text)
    if not match:
        return None
    return float(match.group("height"))


def _extract_budget(text: str) -> dict[str, Any] | None:
    match = re.search(r"(?:预算|总价|费用|控制在)\s*(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>万|千|元)?", text)
    if not match:
        return None
    amount = float(match.group("amount"))
    unit = match.group("unit") or "元"
    multiplier = {"万": 10000, "千": 1000, "元": 1}.get(unit, 1)
    return {"amount": amount * multiplier, "currency": "CNY", "raw_unit": unit}


def _build_clarification_questions(missing_fields: list[str]) -> list[str]:
    questions = {
        "space_type": "请补充要设计的空间类型，例如卧室、客厅、餐厅或办公室。",
        "room_size": "请补充房间长宽或面积。",
        "ceiling_height": "请补充层高。",
    }
    return [questions[field] for field in missing_fields if field in questions]


def extract_requirement_spec(user_text: str) -> dict[str, Any]:
    """把用户自然语言需求转换成 requirement_spec。

    这个函数不调用大模型，目的是让 Step 2A 的结构化结果可复现、可验证。
    识别不到的高风险字段会进入 missing_fields，而不是被系统猜出来。
    """

    text = (user_text or "").strip()
    space_type = _match_keyword_value(text, _SPACE_KEYWORDS)
    style = _match_keyword_value(text, _STYLE_KEYWORDS)
    dimensions = _extract_dimensions(text)
    ceiling_height = _extract_ceiling_height(text)
    budget = _extract_budget(text)

    requirement_spec: dict[str, Any] = {
        "original_text": text,
        "intent_type": "lighting_design" if _contains_any(text, _LIGHTING_INTENT_KEYWORDS) else "unknown",
        "space_type": space_type,
        "style": style,
        "dimensions": dimensions,
        "ceiling_height": ceiling_height,
        "budget": budget,
    }

    missing_fields: list[str] = []
    if not space_type:
        missing_fields.append("space_type")
    if not dimensions:
        missing_fields.append("room_size")
    if ceiling_height is None:
        missing_fields.append("ceiling_height")

    requirement_spec["missing_fields"] = missing_fields
    requirement_spec["clarification_questions"] = _build_clarification_questions(missing_fields)
    return requirement_spec


def merge_requirement_spec(existing_spec: dict[str, Any], user_text: str) -> dict[str, Any]:
    """把用户后续补充的信息合并进已有 requirement_spec。

    只合并用户明确给出的字段；补充文本没有提到的字段继续沿用数据库里的旧值。
    例如用户在上一轮缺层高时回答“高3米”，这里只更新 ceiling_height，不重置空间类型和尺寸。
    """

    existing = dict(existing_spec or {})
    patch = extract_requirement_spec(user_text)

    for key in ("space_type", "style", "ceiling_height", "budget"):
        if patch.get(key) is not None:
            existing[key] = patch[key]

    patch_dimensions = patch.get("dimensions")
    if isinstance(patch_dimensions, dict) and patch_dimensions:
        existing["dimensions"] = patch_dimensions
    else:
        existing.setdefault("dimensions", {})

    if patch.get("intent_type") != "unknown":
        existing["intent_type"] = patch["intent_type"]
    else:
        existing.setdefault("intent_type", "lighting_design")

    existing.setdefault("original_text", patch.get("original_text") or "")
    clarification_texts = list(existing.get("clarification_texts") or [])
    cleaned_text = (user_text or "").strip()
    if cleaned_text:
        clarification_texts.append(cleaned_text)
    existing["clarification_texts"] = clarification_texts

    missing_fields: list[str] = []
    if not existing.get("space_type"):
        missing_fields.append("space_type")
    if not existing.get("dimensions"):
        missing_fields.append("room_size")
    if existing.get("ceiling_height") is None:
        missing_fields.append("ceiling_height")

    existing["missing_fields"] = missing_fields
    existing["clarification_questions"] = _build_clarification_questions(missing_fields)
    return existing
