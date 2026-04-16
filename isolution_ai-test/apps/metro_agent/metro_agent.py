from apps.metro_agent.design_metro import DesignMetro
from apps.req.metro_agent_req import MetroAgentReq
from apps.vo.metro_agent_vo import MetroAgentVo
from apps.metro_agent.construct_metro import ConstructMetro
from apps.metro_agent.control_room_selector import ControlRoomDesign


class MetroAgent:
    def __init__(self):
        pass

    def judge_inputs(self, data: MetroAgentReq):
        code = 200
        return "已为您生成方案", code

    def run(self, data: MetroAgentReq) -> MetroAgentVo:
        # Implement the logic for the MetroAgent here
        msg, code = self.judge_inputs(data)
        if code != 200:
            return MetroAgentVo(
                roomInfo=[],
                planList=[],
                code=code,
                msg=msg,
                outputType=0
            )

        try:
            construct_metro = ConstructMetro()
            roomInfo = []
            planList = []
            if data.inputs.roomType in ["customerService", "客服中心"]:
                roomInfo = construct_metro.build_station_hall(data.inputs)
                design_metro = DesignMetro("SDL方案")
                planList = design_metro.design_customer_service(roomInfo, data.inputs)
            elif data.inputs.roomType in ["stationHall", "站厅"]:
                roomInfo = construct_metro.build_station_hall(data.inputs)
                design_metro = DesignMetro(data.inputs.tag or "清晰光")
                planList = design_metro.design_station_hall(roomInfo, data.inputs)
            elif data.inputs.roomType in ["platform", "站台"]:
                roomInfo = construct_metro.build_platform(data.inputs)
                design_metro = DesignMetro(data.inputs.tag or "高效光")
                planList = design_metro.design_platform(roomInfo, data.inputs)
            elif data.inputs.roomType in ["controlRoom", "控制室"]:
                crd = ControlRoomDesign()
                roomInfo, planList = crd.design_control_room(data.inputs)
            else:
                return MetroAgentVo(roomInfo=[], planList=[], code=400, msg=f"空间类型错误： {data.inputs.roomType}", outputType=0)

            # normalize planList to list[dict]
            if planList is None:
                planList = []
            elif isinstance(planList, dict):
                planList = [planList]

        except Exception as e:
            return MetroAgentVo(roomInfo=[], planList=[], code=500, msg=str(e), outputType=0)

        return MetroAgentVo(
            roomInfo=roomInfo,
            planList=planList,
            code=200,
            msg="方案生成成功",
            outputType=1
        )
