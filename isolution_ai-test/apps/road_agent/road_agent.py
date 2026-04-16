import json
import math
import traceback

from apps.req.road_agent_req import RoadAgentReq
from apps.road_agent.construct_road import ConstructRoad
from apps.road_agent.design_road import DesignRoad
from apps.road_agent.param_agent import ParamAgent
from apps.road_agent.select_prod import select_prod
from apps.vo.road_agent_vo import RoadAgentVo
from apps.vo.road_param_vo import RoadParamVo, Data
from config import LOOGER

param_agent = ParamAgent()
class RoadAgent:
    
    def __init__(self):
        self.max_light_gap = 45

    def judge_inputs(self, data: RoadAgentReq):
        code = 200

        # 1. 布灯方式与灯臂类型校验
        if "单侧" in data.inputs.assembleMethod and data.inputs.lightArmType != "单臂":
            code = 400
            return "单侧布灯方式仅支持单臂灯杆", code
        if data.inputs.assembleMethod == "中心对称" and data.inputs.lightArmType != "平行臂":
            code = 400
            return "中心对称布灯方式仅支持平行臂灯杆", code

        # # 2. 道路等级与布灯方式校验
        # if data.inputs.level == "支路" and data.inputs.assembleMethod not in ["单侧", "单侧左", "单侧右", "双侧交错"]:
        #     code = 400
        #     return "支路仅支持单侧或双侧交错布灯方式", code
        
        # 布灯方式：单侧；灯臂类型：单臂；仅支持新建道路4车道
        if data.inputs.planType == "新建道路":
            if data.inputs.level in ["快速路", "主干路"]:
                if "单侧" in data.inputs.assembleMethod and data.inputs.lightArmType == "单臂":
                    if not any(lane.count == 4 for lane in data.inputs.lanes if lane.type == "机动车道"):
                        code = 400
                        return "新建道路单侧布灯方式仅支持机动车道4车道", code
        
        # 布灯方式：单侧；灯臂类型：单臂；仅2车道
        if data.inputs.level in ["次干路"]:
            if "单侧" in data.inputs.assembleMethod and data.inputs.lightArmType == "单臂":
                if not any(lane.count == 2 for lane in data.inputs.lanes if lane.type == "机动车道"):
                    code = 400
                    return "次干路单侧布灯方式仅支持机动车道2车道", code
                
        # 车道类型数量验证
        if data.inputs.level in ["主干路", "次干路", "支路"]:
            if not any(lane.count == 2 for lane in data.inputs.lanes if lane.type == "人行道"):
                code = 400
                return "主干路、次干路、支路必须有2条人行道", code
        
        # # 灯具改造改造灯具盏数应大于200
        # if data.inputs.planType in ["灯具改造", "EMC"]:
        #     if "单侧" in data.inputs.assembleMethod:
        #         min_light_num = math.ceil(data.inputs.length * 1000 / self.max_light_gap)
        #     elif data.inputs.assembleMethod == "中心对称":
        #         if data.inputs.subLightFlag:
        #             if data.inputs.subLightArmType == "高低臂":
        #                 min_light_num = math.ceil(data.inputs.length * 1000 / self.max_light_gap) * 6
        #             elif data.inputs.subLightArmType == "单臂":
        #                 min_light_num = math.ceil(data.inputs.length * 1000 / self.max_light_gap) * 4
        #         else:
        #             min_light_num = math.ceil(data.inputs.length * 1000 / self.max_light_gap) * 2
        #     elif data.inputs.assembleMethod in ["双侧对称", "双侧交错"]:
        #         if data.inputs.subLightFlag:
        #             if data.inputs.subLightArmType == "高低臂":
        #                 if data.inputs.lightArmType in ["高低臂", "平行臂"]:
        #                     min_light_num = math.ceil(data.inputs.length * 1000 / self.max_light_gap) * 8
        #                 else:
        #                     min_light_num = math.ceil(data.inputs.length * 1000 / self.max_light_gap) * 6
        #             elif data.inputs.subLightArmType == "单臂":
        #                 if data.inputs.lightArmType in ["高低臂", "平行臂"]:
        #                     min_light_num = math.ceil(data.inputs.length * 1000 / self.max_light_gap) * 6
        #                 else:
        #                     min_light_num = math.ceil(data.inputs.length * 1000 / self.max_light_gap) * 4
        #         else:
        #             if data.inputs.lightArmType in ["高低臂", "平行臂"]:
        #                 min_light_num = math.ceil(data.inputs.length * 1000 / self.max_light_gap) * 4
        #             else:
        #                 min_light_num = math.ceil(data.inputs.length * 1000 / self.max_light_gap) * 2
        #     if data.inputs.lightNum < min_light_num:
        #         code = 400
        #         return "{}公里{}{}灯具改造灯具数量应大于{}".format(data.inputs.length, data.inputs.assembleMethod, data.inputs.lightArmType, min_light_num), code

        return "已为您生成方案", code

    def param_run(self, data: RoadAgentReq) -> RoadParamVo:
        
        # 距路边距离
        if data.inputs.lightRoadGap != 0:
            light_road_gap = data.inputs.lightRoadGap
        else:
            light_road_gap = 0.5
            if data.inputs.assembleMethod == "中心对称":
                for lane in data.inputs.lanes:
                    if lane.type in ["绿化带", "水泥墩"] and lane.count == 1:
                        light_road_gap = lane.width / 2
            else:
                for lane in data.inputs.lanes:
                    if lane.type in ["绿化带", "水泥墩"] and lane.count >= 2:
                        light_road_gap = lane.width / 2

        if data.inputs.lightPoleHeight != 0:
            light_pole_height = data.inputs.lightPoleHeight
        else:
            light_pole_height = DesignRoad.cal_light_h(data.inputs)

        # 传入灯间距用传入值，并反算道路距离
        length = data.inputs.length
        if data.inputs.lightGap != 0:
            light_gap = data.inputs.lightGap
            if data.inputs.planType != "新建道路":
                length = DesignRoad.cal_road_length(data.inputs)
        else:
            light_gap = DesignRoad.cal_light_gap(light_pole_height, data.inputs)

        main_lane_num = next((lane.count for lane in data.inputs.lanes if lane.type == "机动车道"), 0)
        res_data = Data(
            lightRoadGap=round(light_road_gap, 2),
            lightPoleHeight=light_pole_height,
            mainLightHeight=data.inputs.mainLightHeight if data.inputs.mainLightHeight != 0 else light_pole_height,
            subLightHeight=data.inputs.subLightHeight if data.inputs.subLightHeight != 0 else light_pole_height - 3,
            mainLightArmLength=data.inputs.mainLightArmLength if data.inputs.mainLightArmLength != 0 else round(light_pole_height / 4, 2),
            subLightArmLength=data.inputs.subLightArmLength if data.inputs.subLightArmLength != 0 else 1,
            mainLightArmAngle=data.inputs.mainLightArmAngle if data.inputs.mainLightArmAngle != 0 else DesignRoad.angle_dict[str(main_lane_num)],
            subLightArmAngle=data.inputs.subLightArmAngle if data.inputs.subLightArmAngle != 0 else DesignRoad.angle_dict[str(main_lane_num)],
            lightGap=round(light_gap, 1),
            length=round(length, 2)
        )

        LOOGER.info(f"Param Res: {res_data.dict()}")
        return RoadParamVo(
            code=200,
            msg="ok",
            data=res_data
        )

    def run(self, data: RoadAgentReq) -> RoadAgentVo:
        # 转为json打印入参
        # import json
        # data = json.loads(data.json())
        msg, code = self.judge_inputs(data)
        if code != 200:
            return RoadAgentVo(
                roomInfo=[],
                planList=[],
                code=code,
                msg=msg,
                outputType=0
            )
        try:
        # if True:
            params = param_agent.run(data.inputs.text, data.user)
            LOOGER.info(f"Params: {params}")
            params_flag, param_msg = param_agent.judge_params(params, data.inputs.lightArmType)
            if not params_flag:
                LOOGER.info(f"Params error: {param_msg}")
                return RoadAgentVo(
                    roomInfo=[],
                    planList=[],
                    code=400,
                    msg=param_msg,
                    outputType=0
                )

            construct_road = ConstructRoad()
            road_ls = construct_road.build_road(data.inputs)
            if data.inputs.level in ["快速路", "主干路", "次干路"]:
                road_ls = construct_road.draw_main_lines(road_ls)
            elif data.inputs.level in ["支路"]:
                road_ls = construct_road.draw_single_lines(road_ls)

            # 添加车辆
            road_ls = construct_road.add_cars(road_ls)
            design_road = DesignRoad(road_ls, data.inputs)

            if data.inputs.assembleMethod in ["单侧", "单侧右"]: 
                planInfo = design_road.design_single_pole(road_ls, data.inputs)
            elif data.inputs.assembleMethod == "单侧左":
                planInfo = design_road.design_single_pole(road_ls, data.inputs, side="left")
            elif data.inputs.assembleMethod == "中心对称":
                planInfo = design_road.design_center_pole(road_ls, data.inputs)
            elif data.inputs.assembleMethod == "双侧对称":
                planInfo = design_road.design_double_para_pole(road_ls, data.inputs)
            elif data.inputs.assembleMethod == "双侧交错":
                planInfo = design_road.design_double_inter_pole(road_ls, data.inputs)

            # 辅助照明
            if data.inputs.subLightFlag and "单侧" not in data.inputs.assembleMethod:
                planInfo = design_road.add_sub_lights(road_ls, planInfo, data.inputs)
            
            # 增加系统平台
            planInfo = design_road.add_platform(planInfo)

            # 灯具改造修改总数
            if data.inputs.planType in ["灯具改造", "EMC"]:
                planInfo["lightNum"] = data.inputs.lightNum
                count_ls = []
                idx_ls = []
                for idx, prod in enumerate(planInfo["products"]):
                    if prod["category2"] == "路灯":
                        count_ls.append(prod["count"])
                        idx_ls.append(idx)
                last_count = data.inputs.lightNum - sum(count_ls[:-1])
                planInfo["products"][idx_ls[-1]]["count"] = last_count
            
            # # 灯具改造修改总数
            # if data.inputs.planType in ["灯具改造", "EMC"]:
            #     planInfo["lightNum"] = data.inputs.lightNum
            #     count_ls = []
            #     idx_ls = []
            #     for idx, prod in enumerate(planInfo["products"]):
            #         if prod["category2"] == "灯杆":
            #             count_ls.append(prod["count"])
            #             idx_ls.append(idx)
            #     last_count = data.inputs.lightNum - sum(count_ls[:-1])
            #     planInfo["products"][idx_ls[-1]]["count"] = last_count

            # 产品选型
            planInfo = select_prod.select(planInfo, params)
            code = 200

        except Exception as e:
            LOOGER.error("Agent Received request: {}".format(json.dumps(data.dict(), ensure_ascii=False)))
            LOOGER.error("Error in RoadAgent run: {}".format(traceback.format_exc()))
            code = 500
            msg = "方案生成失败"
            planInfo = {}

        return RoadAgentVo(
            roomInfo=road_ls,
            planList=[planInfo],
            code=code,
            msg=msg,
            outputType=0
        )
