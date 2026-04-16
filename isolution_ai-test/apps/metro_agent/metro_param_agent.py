"""Metro-specific parameter extraction/validation agent.

This module implements `MetroParamAgent` for extracting and validating
lighting parameters specific to metro/subway projects. It supports:
- Linear fixtures (线形灯具): 朗型, 恒
- Recessed downlights (筒灯): 佳
- Modules (模组): 天幕
- LED strips (低压灯带): 光跃 Ray

The agent uses LLM-based parsing and validates combinations against
the product database.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import MessagesState, StateGraph

from apps.road_agent.llm import req_llm
from apps.road_agent.utils import load_prompt
from apps.road_agent.prod_datasets import prod_dataset


class MetroParamAgent:
    def __init__(self):
        # Load metro-specific prompt or fall back to road prompt
        try:
            self.sys_prompt = load_prompt("prompts/param_sys_prompt_metro.md")
        except (FileNotFoundError, OSError):
            self.sys_prompt = load_prompt("prompts/param_sys_prompt.md")

        self.agent_name = "metro_param_agent"
        self.agent = self.build_param_agent()

        # Metro product series from the shared dataset
        self.metro_linear_series_ls = getattr(
            prod_dataset, "metro_linear_series_ls", []
        )
        self.metro_recessed_series_ls = getattr(
            prod_dataset, "metro_recessed_series_ls", []
        )
        self.metro_module_series_ls = getattr(
            prod_dataset, "metro_module_series_ls", []
        )
        self.metro_led_strip_series_ls = getattr(
            prod_dataset, "metro_led_strip_series_ls", []
        )
        self.metro_fixture_series_ls = getattr(
            prod_dataset, "metro_fixture_series_ls", []
        )

        # Number representations for Chinese/Roman numeral matching
        self.number_dict = {
            "I": ["1", "一", "I", "i"],
            "II": ["2", "二", "II", "ii"],
            "III": ["3", "三", "III", "iii"],
            "IV": ["4", "四", "IV", "iv"],
            "V": ["5", "五", "V", "v"]
        }

    def parse_params(self, state):
        """Use LLM to parse parameters from user input."""
        sys_msg = SystemMessage(content=self.sys_prompt)
        user_msg = HumanMessage(content=state["messages"][0].content)
        messages = [sys_msg, user_msg]
        params = req_llm(messages)
        return {"params": params}

    def build_param_agent(self):
        """Build the parameter extraction agent graph."""
        graph_builder = StateGraph(MessagesState)
        graph_builder.add_node("parse_params", self.parse_params)
        graph_builder.set_entry_point("parse_params")
        graph_builder.set_finish_point("parse_params")
        return graph_builder.compile(name=self.agent_name)

    def run(self, text, user_id):
        """Extract parameters from text using LLM and series matching.

        Args:
            text: User input text describing lighting requirements
            user_id: User identifier for thread management

        Returns:
            dict with keys: linear_series, recessed_series, module_series,
            led_strip_series, colorTemp, power1, power2, lumEff, ra, ip
        """
        res = {
            "linear_series": None,      # 线形灯具系列
            "recessed_series": None,    # 筒灯系列
            "module_series": None,      # 模组系列
            "led_strip_series": None,   # 低压灯带系列
            "colorTemp": None,
            "power1": None,
            "power2": None,
            "lumEff": None,
            "ra": None,                 # 显色指数
            "ip": None,                 # 防护等级
        }

        if not text:
            return res

        # LLM parsing
        messages = [HumanMessage(content=text)]
        config = {"configurable": {"thread_id": user_id}}
        state = MessagesState(
            user_id=user_id, messages=messages, config=config
        )
        result = self.agent.invoke(state)
        params = result.get("params", {}) or {}

        # Extract series by text matching
        linear_series = self.extract_series(
            text, self.metro_linear_series_ls
        )
        recessed_series = self.extract_series(
            text, self.metro_recessed_series_ls
        )
        module_series = self.extract_series(
            text, self.metro_module_series_ls
        )
        led_strip_series = self.extract_series(
            text, self.metro_led_strip_series_ls
        )

        # Populate result
        res["linear_series"] = linear_series
        res["recessed_series"] = recessed_series
        res["module_series"] = module_series
        res["led_strip_series"] = led_strip_series
        res["colorTemp"] = params.get("colorTemp")
        res["power1"] = params.get("power1")
        res["power2"] = params.get("power2")
        res["lumEff"] = params.get("lumEff")
        res["ra"] = params.get("ra")
        res["ip"] = params.get("ip")

        return res

    def extract_series(self, text, series_list):
        """Extract series name from text by matching against series_list.

        Handles Chinese/Roman numeral variations (e.g., III vs 3 vs 三).
        """
        for series in series_list:
            # Check for numeral suffixes
            for n in self.number_dict:
                if series.endswith(n):
                    for num in self.number_dict[n]:
                        variant = series.replace(n, num)
                        if variant in text:
                            return series
                else:
                    if series in text:
                        return series
        return None

    def judge_params(self, params, context=None):
        """Validate metro lighting parameters against product database.

        Args:
            params: dict of extracted parameters
            context: optional dict with context info (e.g., area type)
                     Reserved for future use.

        Returns:
            (bool, str): (is_valid, error_message)
        """
        # Note: context parameter reserved for future enhancement
        _ = context  # Acknowledge unused parameter

        if params is None:
            return False, "参数缺失"

        # 1. Validate linear fixture series with power/colorTemp
        linear_series = params.get("linear_series")
        if linear_series:
            valid, msg = self._validate_fixture_combination(
                linear_series, "线形灯具", params
            )
            if not valid:
                return False, msg

        # 2. Validate recessed downlight series with power/colorTemp
        recessed_series = params.get("recessed_series")
        if recessed_series:
            valid, msg = self._validate_fixture_combination(
                recessed_series, "筒灯", params
            )
            if not valid:
                return False, msg

        # 3. Validate module series with power/colorTemp
        module_series = params.get("module_series")
        if module_series:
            valid, msg = self._validate_fixture_combination(
                module_series, "模组", params
            )
            if not valid:
                return False, msg

        # 4. Validate LED strip series
        led_strip_series = params.get("led_strip_series")
        if led_strip_series:
            valid, msg = self._validate_fixture_combination(
                led_strip_series, "低压灯带", params
            )
            if not valid:
                return False, msg

        # 5. Check minimum luminous efficacy for metro
        lum_eff = params.get("lumEff")
        if lum_eff is not None:
            try:
                if float(lum_eff) < 80:
                    return (
                        False,
                        f"轨交场景建议光效 >= 80 lm/W，当前：{lum_eff}"
                    )
            except (ValueError, TypeError):
                pass

        # 6. Check color rendering index (ra)
        ra = params.get("ra")
        if ra is not None:
            try:
                if float(ra) < 70:
                    return (
                        False,
                        f"轨交场景建议显色指数 >= 70，当前：{ra}"
                    )
            except (ValueError, TypeError):
                pass

        return True, "ok"

    def _validate_fixture_combination(self, series, category, params):
        """Validate that a series/power/colorTemp combination exists.

        Args:
            series: series name (e.g., "朗型", "佳")
            category: product category (e.g., "线形灯具", "筒灯")
            params: dict with colorTemp, power1, etc.

        Returns:
            (bool, str): (is_valid, error_message)
        """
        df = prod_dataset.prod_df
        metro_df = df[df["行业"].str.contains("轨交", na=False)]

        # Filter by category and series
        fixture_df = metro_df[
            (metro_df["一级分类名称"] == category) &
            (metro_df["系列"] == series)
        ]

        if len(fixture_df) == 0:
            return False, f"未找到轨交行业的{category}系列：{series}"

        # Check power if specified
        power1 = params.get("power1")
        if power1:
            try:
                power_val = int(power1)
                power_df = fixture_df[fixture_df["功率(w)"] == power_val]
                if len(power_df) == 0:
                    available_powers = sorted(
                        fixture_df["功率(w)"].dropna().unique().tolist()
                    )
                    return (
                        False,
                        f"{category}系列{series}不支持功率{power1}W，"
                        f"可选功率：{available_powers}W"
                    )
                fixture_df = power_df
            except (ValueError, TypeError):
                pass

        # Check color temperature if specified
        color_temp = params.get("colorTemp")
        if color_temp:
            try:
                ct_val = int(color_temp)
                ct_df = fixture_df[fixture_df["色温(k)"] == ct_val]
                if len(ct_df) == 0:
                    available_cts = sorted(
                        fixture_df["色温(k)"].dropna().unique().tolist()
                    )
                    return (
                        False,
                        f"{category}系列{series}不支持色温{color_temp}K，"
                        f"可选色温：{available_cts}K"
                    )
            except (ValueError, TypeError):
                pass

        return True, "ok"
