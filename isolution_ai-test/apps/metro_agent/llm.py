from langchain_openai import ChatOpenAI
import json
import re
from config import API_KEY, API_URL, PARAM_MODEL_NAME


def req_llm(messages):
    """请求大模型"""
    llm = ChatOpenAI(
        model=PARAM_MODEL_NAME,
        openai_api_base=API_URL,
        openai_api_key=API_KEY,
        temperature=0,
        max_tokens=4096,
    )
    res = llm.invoke(messages).content
    print(f"llm res: {res}")
    # 使用正则表达式提取JSON部分
    json_match = re.search(r'```json\n({.*?})\n```', res, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # 如果没有找到markdown格式，尝试直接解析
        json_str = res

    try:
        res = json.loads(json_str)
    except json.JSONDecodeError:
        # 如果解析失败，尝试去除任何可能的前后文
        match = re.search(r'{.*}', res, re.DOTALL)
        if match:
            res = json.loads(match.group(0))
        else:
            # 如果还是失败，就返回一个空字典或者抛出错误
            print("Failed to decode JSON from LLM response.")
            return {}
            
    return res
