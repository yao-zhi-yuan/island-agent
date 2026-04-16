import os

from langchain.chat_models import init_chat_model
from langchain_community.chat_models import ChatTongyi
from langchain_openai import ChatOpenAI


def build_qwen_llm(model_name: str):
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is not set; please export your Qianwen API key.")
    if not model_name:
        model_name = os.getenv("TONGYI_MODEL", "qwen3.5-plus")

    # qwen3.5/qwen3.6 系列走 DashScope OpenAI 兼容接口，工具调用和流式输出更稳定。
    if model_name.startswith(("qwen3.5-", "qwen3.6-")):
        base_url = os.getenv(
            "DASHSCOPE_COMPAT_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        return ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url, streaming=True)

    return ChatTongyi(model=model_name, api_key=api_key)

def build_deepseek_llm(model_name: str):
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set; please export your Deepseek API key.")
    if not model_name:
        model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    return init_chat_model(model_name=model_name,streaming=True)
