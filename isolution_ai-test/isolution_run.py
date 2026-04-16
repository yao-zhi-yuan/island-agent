import argparse
import json
import uvicorn
from fastapi import FastAPI, Request

from apps.road_agent.road_agent import RoadAgent
from apps.metro_agent.metro_agent import MetroAgent
from apps.metro_agent.metro_param_agent import MetroParamAgent
from apps.req.road_agent_req import RoadAgentReq
from apps.req.metro_agent_req import MetroAgentReq
from apps.vo.road_agent_vo import RoadAgentVo
from apps.vo.road_param_vo import RoadParamVo
from apps.vo.metro_param_vo import MetroParamVo
from apps.hospital_agent.router import router as hospital_router
from config import LOOGER, TEST_PORT, PROD_PORT, DEV_PORT

app = FastAPI()
# Include hospital router
app.include_router(hospital_router, tags=["hospital"])

road_agent = RoadAgent()
metro_agent = MetroAgent()
metro_param_agent = MetroParamAgent()

@app.post(
        "/road_agent", 
        summary="道路智能体",
        description="道路智能体设计接口",
        response_model=RoadAgentVo)
async def road_agent_func(request: Request):
    body = await request.json()
    LOOGER.info("RoadAgent Received request: {}".format(json.dumps(body, ensure_ascii=False)))
    try:
        item = RoadAgentReq.model_validate(body)
    except Exception as e:
        LOOGER.error("RoadAgent Received request: {}".format(json.dumps(body, ensure_ascii=False)))
        LOOGER.error("Validation error: {}".format(str(e)))
        return RoadAgentVo(
            roomInfo=[],
            planList=[],
            code=400,
            msg=str(e),
            outputType=0
        )
    
    res = road_agent.run(item)

    return res

@app.post(
        "/road_param", 
        summary="道路智能体参数计算",
        description="道路智能体参数计算接口",
        response_model=RoadParamVo)
async def road_param_func(request: Request):
    body = await request.json()
    LOOGER.info("RoadParam Req: {}".format(json.dumps(body, ensure_ascii=False)))
    try:
        item = RoadAgentReq.model_validate(body)
    except Exception as e:
        LOOGER.error("RoadParam Req: {}".format(json.dumps(body, ensure_ascii=False)))
        LOOGER.error("Validation error: {}".format(str(e)))
        return RoadParamVo(
            code=400,
            msg=str(e),
            data=None
        )
    
    res = road_agent.param_run(item)

    return res

@app.post(
        "/metro_agent", 
        summary="轨交智能体",
        description="轨交智能体设计接口",
        response_model=RoadAgentVo)
async def metro_agent_func(request: Request):
    body = await request.json()
    LOOGER.info("MetroAgent Received request: {}".format(json.dumps(body, ensure_ascii=False)))
    try:
        item = MetroAgentReq.model_validate(body)
    except Exception as e:
        LOOGER.error("MetroAgent Received request: {}".format(json.dumps(body, ensure_ascii=False)))
        LOOGER.error("Validation error: {}".format(str(e)))
        return RoadAgentVo(
            roomInfo=[],
            planList=[],
            code=400,
            msg=str(e),
            outputType=0
        )
    
    res = metro_agent.run(item)

    return res

@app.post(
        "/metro_param",
        summary="地铁参数抽取",
        description="地铁参数抽取与校验接口",
        response_model=MetroParamVo)
async def metro_param_func(request: Request):
    body = await request.json()
    LOOGER.info("MetroParam Req: {}".format(json.dumps(body, ensure_ascii=False)))
    text = body.get("text", "")
    user_id = body.get("user_id", "default")

    try:
        params = metro_param_agent.run(text, user_id)
    except Exception as e:
        LOOGER.error("MetroParam error: {}".format(str(e)))
        return MetroParamVo(code=500, msg=str(e), data=None)

    ok, msg = metro_param_agent.judge_params(params)
    data = {"params": params, "ok": ok, "msg": msg}

    return MetroParamVo(code=200, msg="ok", data=data)


from apps.office_agent.router import router as office_router
from apps.hospital_agent.router import router as hospital_router
app.include_router(office_router)
app.include_router(hospital_router)

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--env", type=str, default="dev", help="运行环境: test/prod")
    args = parser.parse_args()

    print(f"当前运行环境: {args.env}")

    uvicorn.run(app, host="0.0.0.0", port=eval(f"{args.env.upper()}_PORT"))