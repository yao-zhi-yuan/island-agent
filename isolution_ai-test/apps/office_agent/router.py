import json
from fastapi import APIRouter, Request
from config import LOOGER
from apps.office_agent.office_design import OfficeDesign
from apps.req.office_agent_req import OfficeAgentReq
from apps.vo.office_agent_vo import OfficeAgentVo

router = APIRouter(prefix="/office", tags=["OfficeDesign"])
office_design = OfficeDesign()

@router.post(
    "/design",
    summary="OfficeAgent 办公空间设计",
    description="办公空间智能照明设计接口",
    response_model=OfficeAgentVo
)
async def office_design_func(request: Request):
    """办公空间设计接口"""
    body = await request.json()
    LOOGER.info("OfficeAgent Received request: {}".format(json.dumps(body, ensure_ascii=False)))
    
    try:
        item = OfficeAgentReq.model_validate(body)
    except Exception as e:
        LOOGER.error("OfficeAgent Received request: {}".format(json.dumps(body, ensure_ascii=False)))
        LOOGER.error("Validation error: {}".format(str(e)))
        return OfficeAgentVo(
            roomInfo=[],
            planList=[],
            code=400,
            msg=str(e),
            outputType=0
        )
    
    try:
        room_list, plan_list = office_design.design_office(item.inputs)
        return OfficeAgentVo(
            roomInfo=room_list,
            planList=plan_list,
            code=200,
            msg="ok",
            outputType=0
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        LOOGER.error("OfficeAgent Error: {}".format(str(e)))
        return OfficeAgentVo(
            roomInfo=[],
            planList=[],
            code=500,
            msg=str(e),
            outputType=0
        )
