from fastapi import APIRouter
import json
from apps.req.hospital_agent_req import HospitalInputs, HospitalAgentReq
from apps.vo.hospital_agent_vo import HospitalAgentVo
from apps.hospital_agent.hospital_design import HospitalDesign

router = APIRouter()
designer = HospitalDesign()

@router.post("/hospital/design", response_model=HospitalAgentVo)
async def design_hospital(req: HospitalAgentReq):
    try:
        room_list, plan_list, outer_poly = designer.design_hospital(req.inputs)
        return HospitalAgentVo(
            roomInfo=room_list,
            planList=plan_list,
            outer_poly=json.dumps(outer_poly) if outer_poly else None,
            code=200,
            msg="success",
            outputType=0
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HospitalAgentVo(
            roomInfo=[],
            planList=[],
            outer_poly=None,
            code=400,
            msg=str(e),
            outputType=0
        )
