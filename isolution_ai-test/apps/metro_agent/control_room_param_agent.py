from typing import Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import MessagesState, StateGraph
import re

from apps.metro_agent.llm import req_llm
from apps.road_agent.utils import load_prompt


class _MessagesState(MessagesState):
    user_id: str
    params: dict = {}


class ControlRoomParamAgent:
    """Agent for extracting control room lighting parameters.

    Returns JSON fields:
    - series: 灯具系列名称，例如 "天境", "佳IV"
    - colorTemp: 色温值字符串，例如 "4000"，无则为 None
    - size: 面板尺寸，统一返回如 "600*600" 或 "600*1200"
    """
    
    def __init__(self):
        self.sys_prompt = load_prompt(
            "prompts/control_room_param_sys_prompt.md"
        )
        self.agent_name = "control_room_param_agent"
        self.agent = self._build_agent()
        # Mapping numerals to support normalization like 佳4 -> 佳IV
        self.number_dict = {
            "I": ["1", "一", "I", "i"],
            "II": ["2", "二", "II", "ii"],
            "III": ["3", "三", "III", "iii"],
            "IV": ["4", "四", "IV", "iv"],
            "V": ["5", "五", "V", "v"],
            "VI": ["6", "六", "VI", "vi"],
            "VII": ["7", "七", "VII", "vii"],
            "VIII": ["8", "八", "VIII", "viii"],
            "IX": ["9", "九", "IX", "ix"],
            "X": ["10", "十", "X", "x"],
        }

    def _build_agent(self):
        graph = StateGraph(_MessagesState)
        graph.add_node("parse_params", self._parse_params)
        graph.set_entry_point("parse_params")
        graph.set_finish_point("parse_params")
        return graph.compile(name=self.agent_name)

    def _parse_params(self, state):
        sys_msg = SystemMessage(content=self.sys_prompt)
        user_msg = HumanMessage(content=state["messages"][0].content)
        messages = [sys_msg, user_msg]
        params = req_llm(messages)
        return {"params": params}

    def run(self, text: str, user_id: str):
        res = {"series": None, "colorTemp": None, "size": None}
        if not text:
            return res

        messages = [HumanMessage(content=text)]
        config = {"configurable": {"thread_id": user_id}}
        state = _MessagesState(
            user_id=user_id, messages=messages, config=config
        )
        result = self.agent.invoke(state) or {}
        params = result.get("params", {}) or {}

        series = self._normalize_series(params.get("series"))
        color_temp = params.get("colorTemp")
        size = self._normalize_size(
            params.get("size") or self._extract_size_from_text(text)
        )

        res["series"] = series
        res["colorTemp"] = color_temp if color_temp not in ("", None) else None
        res["size"] = size
        return res

    def _normalize_series(self, series: Optional[str]) -> Optional[str]:
        if not series or not isinstance(series, str):
            return series
        # Trim spaces
        s = series.strip()
        # Normalize trailing numerals to Roman (upper)
        for roman, variants in self.number_dict.items():
            for v in sorted(variants, key=len, reverse=True):
                if s.endswith(v):
                    return s[: len(s) - len(v)] + roman
        return s

    def _normalize_size(self, size: Optional[str]) -> Optional[str]:
        """Normalize size to 'W*H' in millimeters, e.g., '600*1200'.
        Accepts formats like '0.6x1.2m', '0.6x1.2', '600x1200',
        '600×1200mm', '600*600'.
        """
        if not size or not isinstance(size, str):
            return None
        raw = size.strip().lower().replace("ｍ", "m").replace("㎜", "mm")
        # Replace common separators to '*'
        raw = re.sub(r"[x×X]", "*", raw)
        raw = re.sub(r"\s+", "", raw)

        # Case 1: explicit meters (contains 'm' but not 'mm')
        if re.search(r"\dm|\d\.\d+m", raw) and "mm" not in raw:
            parts = re.split(r"\*", raw.replace("m", ""))
            try:
                w = int(round(float(parts[0]) * 1000))
                h = int(round(float(parts[1]) * 1000))
                return f"{w}*{h}"
            except Exception:
                return None

        # Case 2: no unit, but decimals present -> treat as meters
        if ("mm" not in raw and "m" not in raw and
                re.search(r"\d+\.\d+\*\d+\.\d+", raw)):
            try:
                p = raw.split("*")
                w = int(round(float(p[0]) * 1000))
                h = int(round(float(p[1]) * 1000))
                return f"{w}*{h}"
            except Exception:
                return None

        # Case 3: millimeters explicitly
        raw = raw.replace("mm", "")
        parts = re.split(r"\*", raw)
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return f"{int(parts[0])}*{int(parts[1])}"

        # Fallback: extract two numbers; if decimals exist, assume meters
        nums = re.findall(r"\d+(?:\.\d+)?", raw)
        if len(nums) >= 2:
            try:
                a = float(nums[0])
                b = float(nums[1])
                decimals = ("." in nums[0]) or ("." in nums[1])
                small_vals = (a <= 20 and b <= 20)
                if decimals or small_vals:
                    return f"{int(round(a * 1000))}*{int(round(b * 1000))}"
                return f"{int(round(a))}*{int(round(b))}"
            except Exception:
                pass
        return None

    def _extract_size_from_text(self, text: str) -> Optional[str]:
        """Fallback: extract a size hint directly from input text."""
        if not text:
            return None
        m = re.search(
            r"(\d+(?:\.\d+)?)\s*[x×X*]\s*(\d+(?:\.\d+)?)(m{1,2})?",
            text,
            re.IGNORECASE,
        )
        if not m:
            return None
        w, h, unit = m.group(1), m.group(2), (m.group(3) or "")
        unit = unit.lower()
        try:
            wf = float(w)
            hf = float(h)
        except Exception:
            return None
        if unit == "m":
            return f"{int(round(wf * 1000))}*{int(round(hf * 1000))}"
        # If unit missing: heuristics
        if unit == "":
            if ("." in w) or ("." in h) or (wf <= 20 and hf <= 20):
                return f"{int(round(wf * 1000))}*{int(round(hf * 1000))}"
            return f"{int(round(wf))}*{int(round(hf))}"
        # unit == 'mm'
        return f"{int(round(wf))}*{int(round(hf))}"
