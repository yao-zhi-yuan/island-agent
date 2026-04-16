import json

from langchain_openai import ChatOpenAI

from config import API_KEY, API_URL, PARAM_MODEL_NAME

control_model = ChatOpenAI(
    model=PARAM_MODEL_NAME,
    api_key=API_KEY,
    base_url=API_URL,
    streaming=True,
    extra_body={
        "enable_thinking": False,
        },
    temperature=0.8,
    )

def req_llm(messages):

    response = control_model.invoke(messages)

    answer_content = response.content

    res = answer_content.split("```json\n")[-1]
    res = res.replace("\n```", "")
    res = json.loads(res)

    return res