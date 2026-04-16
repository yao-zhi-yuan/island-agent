from typing import Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import MessagesState, StateGraph
import re

from apps.metro_agent.llm import req_llm
from apps.road_agent.utils import load_prompt


class _MessagesState(MessagesState):
    user_id: str
    params: dict = {}


class OfficeParamAgent:
    """Agent for extracting office lighting parameters."""
    
    def __init__(self, sys_prompt_path: str = "apps/office_agent/prompts/independent_office_prompt.md"):
        self.sys_prompt = load_prompt(sys_prompt_path)
        self.agent_name = "office_param_agent"
        self.agent = self._build_agent()

    def _build_agent(self):
        graph = StateGraph(_MessagesState)
        graph.add_node("parse_params", self._parse_params)
        graph.set_entry_point("parse_params")
        graph.set_finish_point("parse_params")
        return graph.compile(name=self.agent_name)

    def _parse_params(self, state):
        sys_msg = SystemMessage(content=self.sys_prompt)
        # Use the first message content which is the user input
        user_msg = HumanMessage(content=state["messages"][0].content)
        messages = [sys_msg, user_msg]
        params = req_llm(messages)
        return {"params": params}

    def run(self, text: str, user_id: str):
        if not text:
            return {}

        messages = [HumanMessage(content=text)]
        config = {"configurable": {"thread_id": user_id}}
        state = _MessagesState(
            user_id=user_id, messages=messages, config=config
        )
        result = self.agent.invoke(state) or {}
        params = result.get("params", {}) or {}

        return params
