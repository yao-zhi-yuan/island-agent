

from copy import deepcopy
import json
from apps.req.road_agent_req import Inputs


class DesignRoad:
    """
    Class to design roads based on given parameters.
    """
    gap_dict = {
        "双侧交错": 0.8,
        "双侧对称": 0.6, 
        "中心对称": 1.2,
        "单侧": 1.2,
        "单侧左": 1.2,
        "单侧右": 1.2,
    }
    angle_dict = {
        "1": 5,
        "2": 5,
        "4": 10,
        "6": 15,
        "8": 15,
        "10": 15
    }

    max_light_h_dict = {
        "快速路": {4:12, 6:12, 8:12, 10:13},
        "主干路": {4:12, 6:12, 8:12, 10:13},
        "次干路": {2:12, 4:12, 6:12},
        "支路": {1:9, 2:9}
    }

    light_height_ratio = {
            "快速路": 3,
            "主干路": 3,
            "次干路": 3.5,
            "支路": 3.5
    }
    
    def __init__(self, roomList, data: Inputs):

        self.design_concept_dict = {
            "快速路": "满足较高交通流量在夜间的行车安全及夜间交通的视觉舒适度。照明效果满足主干道夜间快速行车的交通安全、视觉舒适、及节能环保及光污染控制等多重需求。",
            "主干路": "满足较高交通流量在夜间的行车安全及夜间交通的视觉舒适度。照明效果满足主干道夜间快速行车的交通安全、视觉舒适、及节能环保及光污染控制等多重需求。",
            "次干路": "满足道路交通的基本夜间照明需求与交通视觉的舒适性",
            "支路": "满足夜间局部交通的基本照明，达到一般的通行效率"
        }
        
        self.person_light_gap = data.lightRoadGap
        self.power_dict = json.load(open("data/light_power_config.json", "r", encoding="utf-8"))

        self.level = "快速路" if data.level == "主干路" else data.level
        self.main_lane_num = next((lane.count for lane in data.lanes if lane.type == "机动车道"), 0)
        self.sub_lane_num = next((lane.count for lane in data.lanes if lane.type == "辅道"), 0)
        self.bike_lane_num = next((lane.count for lane in data.lanes if lane.type == "非机动车道"), 0)
        self.person_lane_num = next((lane.count for lane in data.lanes if lane.type == "人行道"), 0)
        self.main_lane_w = 0
        self.sub_lane_w = 0
        for lane in data.lanes:
            if lane.type == "机动车道":
                self.main_lane_w = lane.width
            elif lane.type == "辅道":
                self.sub_lane_w += lane.width

        self.mid_tree_num, self.side_tree_num = self.get_tree_num(roomList)
        self.road_w = roomList[0]["rectangle"]["x_max"]
        self.fake_road_h = roomList[0]["rectangle"]["y_max"]
        self.real_road_h = data.length * 1000

        self.light_h = data.lightPoleHeight
        self.light_gap = data.lightGap
                
        self.fake_light_num = round(self.fake_road_h / self.light_gap) + 1
        self.real_light_num = round(self.real_road_h / self.light_gap) + 1
        self.planInfo = {
            "id": 1,
            "name": "节能光方案",
            "designConcept": self.design_concept_dict[data.level],
            "sellingKeywords": "欧普节能光",
            "sellingDescription": "绿色照明、智能调光、高效节能",
            "lightPoleHeight": data.lightPoleHeight,
            "lightRoadGap": data.lightRoadGap,
            "mainLightHeight": data.mainLightHeight,
            "subLightHeight": data.subLightHeight,
            "mainLightArmLength": data.mainLightArmLength,
            "subLightArmLength": data.subLightArmLength,
            "mainLightArmAngle": data.mainLightArmAngle,
            "subLightArmAngle": data.subLightArmAngle,
            "mainLightAngle": data.mainLightAngle,
            "subLightAngle": data.subLightAngle,
            "lightMaintenanceFactor": data.lightMaintenanceFactor,
            "lightGap": self.light_gap,
        }

        self.assemble_method = data.assembleMethod if "单侧" not in data.assembleMethod else "单侧"

    @classmethod
    def cal_light_gap(cls, light_h, data: Inputs):

        # real_road_h = data.length * 1000
        light_gap = light_h * cls.light_height_ratio[data.level]
        # if data.planType == "新建道路":
        #     light_gap = light_h * cls.light_height_ratio[data.level]
        # elif data.planType in ["灯具改造", "EMC"]:
        #     if data.assembleMethod in ["单侧", "单侧右", "单侧左"]:
        #         light_gap = real_road_h / (data.lightNum - 1)
        #     elif data.assembleMethod == "中心对称":
        #         if data.subLightFlag:
        #             if data.subLightArmType == "高低臂":
        #                 light_gap = real_road_h / (data.lightNum / 6 - 1)
        #             elif data.subLightArmType == "单臂":
        #                 light_gap = real_road_h / (data.lightNum / 4 - 1)
        #         else:
        #             light_gap = real_road_h / (data.lightNum / 2 - 1)
        #     elif data.assembleMethod in ["双侧对称", "双侧交错"]:
        #         if data.subLightFlag:
        #             if data.subLightArmType == "高低臂":
        #                 if data.lightArmType in ["高低臂", "平行臂"]:
        #                     light_gap = real_road_h / (data.lightNum / 8 - 1)
        #                 else:
        #                     light_gap = real_road_h / (data.lightNum / 6 - 1)
        #             elif data.subLightArmType == "单臂":
        #                 if data.lightArmType in ["高低臂", "平行臂"]:
        #                     light_gap = real_road_h / (data.lightNum / 6 - 1)
        #                 else:
        #                     light_gap = real_road_h / (data.lightNum / 4 - 1)
        #         else:
        #             if data.lightArmType in ["高低臂", "平行臂"]:
        #                 light_gap = real_road_h / (data.lightNum / 4 - 1)
        #             else:
        #                 light_gap = real_road_h / (data.lightNum / 2 - 1)

        return round(light_gap, 1)
    
    @classmethod
    def cal_road_length(cls, data: Inputs):
        length = data.length
        if data.assembleMethod in ["单侧", "单侧右", "单侧左"]:
            length = (data.lightNum - 1) * data.lightGap / 1000
        elif data.assembleMethod == "中心对称":
            if data.subLightFlag:
                if data.subLightArmType == "高低臂":
                    length = (data.lightNum / 6 - 1) * data.lightGap / 1000
                elif data.subLightArmType == "单臂":
                    length = (data.lightNum / 4 - 1) * data.lightGap / 1000
            else:
                length = (data.lightNum / 2 - 1) * data.lightGap / 1000
        elif data.assembleMethod in ["双侧对称", "双侧交错"]:
            if data.subLightFlag:
                if data.subLightArmType == "高低臂":
                    if data.lightArmType in ["高低臂", "平行臂"]:
                        length = (data.lightNum / 8 - 1) * data.lightGap / 1000
                    else:
                        length = (data.lightNum / 6 - 1) * data.lightGap / 1000
                elif data.subLightArmType == "单臂":
                    if data.lightArmType in ["高低臂", "平行臂"]:
                        length = (data.lightNum / 6 - 1) * data.lightGap / 1000
                    else:
                        length = (data.lightNum / 4 - 1) * data.lightGap / 1000
            else:
                if data.lightArmType in ["高低臂", "平行臂"]:
                    length = (data.lightNum / 4 - 1) * data.lightGap / 1000
                else:
                    length = (data.lightNum / 2 - 1) * data.lightGap / 1000

        return length

    
    @classmethod
    def cal_light_h(cls, data: Inputs):
        main_lane_w = 0
        for lane in data.lanes:
            if lane.type == "机动车道":
                main_lane_w = lane.width

        min_light_h = 6
        main_lane_num = next((lane.count for lane in data.lanes if lane.type == "机动车道"), 0)
        car_w = main_lane_w * main_lane_num
        max_light_h = cls.max_light_h_dict[data.level][main_lane_num]
        assemble_method = data.assembleMethod if "单侧" not in data.assembleMethod else "单侧"
        light_h = round(max(min_light_h, min(car_w * cls.gap_dict[assemble_method], max_light_h)))

        return light_h
    
    def get_tree_num(self, roomList):
        """获取分隔路数量"""

        mid_tree_num = 0
        side_tree_num = 0
        for room in roomList:
            for obj in room.get("objects", []):
                if obj["type"] in ["tree", "concrete", "guardrail"]:
                    if len(obj["locations"]) == 1:
                        mid_tree_num = 1
                    elif len(obj["locations"]) >= 2:
                        side_tree_num = len(obj["locations"])
                
        return mid_tree_num, side_tree_num
    
    def design_single_pole(self, roomList, data: Inputs, side="right") -> dict:
        """单侧布灯-仅单臂"""

        light_locs = []
        if side == "right":
            key_idx_2 = 1
            key_idx_3 = 1
        else:
            key_idx_2 = 0
            key_idx_3 = 0

        # 两侧绿化带
        if self.side_tree_num >= 2: 
            for lane in roomList[0]["objects"]:
                if lane["type"] in ["tree", "concrete", "guardrail"] and len(lane["locations"]) >= 2:
                    light_x = lane["locations"][key_idx_2]["x"]
                    key_road_w = lane["locations"][key_idx_2]["w"]
                    if light_x < self.road_w / 2:
                        light_x = light_x + key_road_w / 2 - self.person_light_gap
                    else:
                        light_x = light_x - key_road_w / 2 + self.person_light_gap
                    break
        # 放到人行道上
        elif self.person_lane_num > 0:
            for lane in roomList[0]["objects"]:
                if lane["type"] == "person_road":
                    light_x = lane["locations"][key_idx_3]["x"]
                    key_road_w = lane["locations"][key_idx_3]["w"]
                    if light_x < self.road_w / 2:
                        light_x = light_x + key_road_w / 2 - self.person_light_gap
                    else:
                        light_x = light_x - key_road_w / 2 + self.person_light_gap
        elif self.sub_lane_num > 0:
            light_x = self.road_w / 2
            light_dis = 0
            key_road_w = 0
            for lane in roomList[0]["objects"]:
                if lane["type"] == "sub_road":
                    for loc in lane["locations"]:
                        x = loc["x"]
                        dis = abs(self.road_w / 2 - x)
                        if dis > light_dis:
                            light_dis = dis
                            light_x = x
                            key_road_w = loc["w"]

            if light_x < self.road_w / 2:
                light_x -= key_road_w / 2
            else:
                light_x += key_road_w / 2
        else:
            light_x = self.road_w / 2
            light_dis = 0
            key_road_w = 0
            for lane in roomList[0]["objects"]:
                if lane["type"] == "main_road":
                    for loc in lane["locations"]:
                        x = loc["x"]
                        dis = abs(self.road_w / 2 - x)
                        if dis >= light_dis:
                            light_dis = dis
                            light_x = x
                            key_road_w = loc["w"]

            if light_x < self.road_w / 2:
                light_x -= key_road_w / 2
            else:
                light_x += key_road_w / 2

        r_z = 0
        if light_x > self.road_w / 2:
            r_z = 180

        for i in range(self.fake_light_num):
            light_locs.append({
                "x": light_x,
                "y": i * self.light_gap,
                "z": self.light_h / 2,
                "w": 1,
                "h": 1,
                "l": self.light_h,
                "rotation": [0, 0, r_z]
            })

        angle = self.__class__.angle_dict[str(self.main_lane_num)]
        poles = {
            "materialCode": None,
            "category1": "道路灯具",
            "category2": "灯杆",
            "lightArmType": "单臂",
            "location": light_locs,
            "lumen": None,
            "count": self.real_light_num,
            "angle": [0, 0, 0, 0, 0, 1],
            "elevationAngle": angle,
            "lightBulb": [{
                "materialCode": None,
                "power": self.power_dict[self.level][self.assemble_method][str(self.main_lane_num)]["right"],
                "pos": "right"
            }]
            }
        
        lights = {
            "materialCode": None,
            "category1": "道路灯具",
            "category2": "路灯",
            "location": light_locs,
            "power": self.power_dict[self.level][self.assemble_method][str(self.main_lane_num)]["right"],
            "count": self.real_light_num,
            "pos": "right"
        }

        planInfo = deepcopy(self.planInfo)
        planInfo["products"] = [poles, lights]
        planInfo["lightNum"] = self.real_light_num

        return planInfo
    
    def design_center_pole(self, roomList, data: Inputs) -> dict:
        """中心对称布灯-仅平行臂"""

        light_x = 0
        for lane in roomList[0]["objects"]:
            if lane["type"] in ["tree", "concrete", "guardrail"] and len(lane["locations"]) == 1:
                light_x = lane["locations"][0]["x"]
                key_road_w = lane["locations"][0]["w"]
                light_x = light_x - key_road_w / 2 + self.person_light_gap
                break

        light_locs = []
        for i in range(self.fake_light_num):
            light_locs.append({
                "x": light_x,
                "y": i * self.light_gap,
                "z": self.light_h / 2,
                "w": 1,
                "h": 1,
                "l": self.light_h,
                "rotation": [0, 0, 0]
            })

        angle = self.__class__.angle_dict[str(self.main_lane_num)]
        power_r = self.power_dict[self.level][self.assemble_method][str(self.main_lane_num)]["right"]
        power_l = self.power_dict[self.level][self.assemble_method][str(self.main_lane_num)]["left"]
        if data.level in ["快速路", "主干路"] and self.main_lane_num in [6, 8] and data.lightArmType == "平行臂":
            power_r = 250
            power_l = 250
        poles = {
            "materialCode": None,
            "category1": "道路灯具",
            "category2": "灯杆",
            "lightArmType": "平行臂",
            "location": light_locs,
            "lumen": None,
            "count": self.real_light_num,
            "angle": [0, 0, 0, 0, 0, 1],
            "elevationAngle": angle,
            "lightBulb": [{
                "materialCode": None,
                "power": power_r,
                "pos": "right"
            },
            {
                "materialCode": None,
                "power": power_l,
                "pos": "left"
            }
            ]
        }
        
        lights_1 = {
            "materialCode": None,
            "category1": "道路灯具",
            "category2": "路灯",
            "location": light_locs,
            "power": power_r,
            "count": self.real_light_num,
            "pos": "right"
        }
        lights_2 = {
            "materialCode": None,
            "category1": "道路灯具",
            "category2": "路灯",
            "location": light_locs,
            "power": power_l,
            "count": self.real_light_num,
            "pos": "left"
        }

        planInfo = deepcopy(self.planInfo)
        planInfo["products"] = [poles, lights_1, lights_2]
        planInfo["lightNum"] = self.real_light_num * 2

        return planInfo
    
    def design_double_para_pole(self, roomList, data: Inputs) -> dict:
        """双侧对称布灯-仅高低臂、单臂"""

        # 两边绿化带取第1,2个
        if self.side_tree_num >= 2:
            for lane in roomList[0]["objects"]:
                if lane["type"] in ["tree", "concrete", "guardrail"] and len(lane["locations"]) >= 2:
                    light_x_1 = lane["locations"][0]["x"]
                    light_x_2 = lane["locations"][1]["x"]
                    key_road_w_1 = lane["locations"][0]["w"]
                    key_road_w_2 = lane["locations"][1]["w"]
                    if light_x_1 < self.road_w / 2:
                        light_x_1 = light_x_1 + key_road_w_1 / 2 - self.person_light_gap
                        light_x_2 = light_x_2 - key_road_w_2 / 2 + self.person_light_gap
                    else:
                        light_x_1 = light_x_1 - key_road_w_1 / 2 + self.person_light_gap
                        light_x_2 = light_x_2 + key_road_w_2 / 2 - self.person_light_gap
                    break
        # # 辅路边上 4 辅道除外
        # elif 0 < self.sub_lane_num < 4:
        #     for lane in roomList[0]["objects"]:
        #         if lane["type"] == "sub_road":
        #             key_road_w = lane["locations"][0]["w"]
        #             light_x_1 = lane["locations"][-2]["x"]
        #             light_x_2 = lane["locations"][-1]["x"]

        #     if light_x_1 < self.road_w / 2:
        #         light_x_1 -= key_road_w / 2
        #         light_x_2 += key_road_w / 2
        #     else:
        #         light_x_1 += key_road_w / 2
        #         light_x_2 -= key_road_w / 2
        # 放到人行道上
        elif self.person_lane_num == 2:
            for lane in roomList[0]["objects"]:
                if lane["type"] == "person_road":
                    light_x_1 = lane["locations"][0]["x"]
                    key_road_w_1 = lane["locations"][0]["w"]
                    light_x_2 = lane["locations"][1]["x"]
                    key_road_w_2 = lane["locations"][1]["w"]
                    if light_x_1 < self.road_w / 2:
                        light_x_1 = light_x_1 + key_road_w_1 / 2 - self.person_light_gap
                        light_x_2 = light_x_2 - key_road_w_2 / 2 + self.person_light_gap
                    else:
                        light_x_1 = light_x_1 - key_road_w_1 / 2 + self.person_light_gap
                        light_x_2 = light_x_2 + key_road_w_2 / 2 - self.person_light_gap
                    break
        # 主路边上
        else:
            for lane in roomList[0]["objects"]:
                if lane["type"] == "main_road":
                    key_road_w = lane["locations"][0]["w"]
                    light_x_1 = lane["locations"][-2]["x"]
                    light_x_2 = lane["locations"][-1]["x"]
                            
            if light_x_1 < self.road_w / 2:
                light_x_1 -= key_road_w / 2
                light_x_2 += key_road_w / 2
            else:
                light_x_1 += key_road_w / 2
                light_x_2 -= key_road_w / 2

        r_z_1 = 0
        r_z_2 = 180
        if light_x_1 > self.road_w / 2:
            r_z_1 = 180
            r_z_2 = 0

        light_locs_1 = []
        for i in range(self.fake_light_num):
            light_locs_1.append({
                "x": light_x_1,
                "y": i * self.light_gap,
                "z": self.light_h / 2,
                "w": 1,
                "h": 1,
                "l": self.light_h,
                "rotation": [0, 0, r_z_1]
            })

        light_locs_2 = []
        for i in range(self.fake_light_num):
            light_locs_2.append({
                "x": light_x_2,
                "y": i * self.light_gap,
                "z": self.light_h / 2,
                "w": 1,
                "h": 1,
                "l": self.light_h,
                "rotation": [0, 0, r_z_2]
            })

        angle = self.__class__.angle_dict[str(self.main_lane_num)]
        power_r = self.power_dict[self.level][self.assemble_method][str(self.main_lane_num)]["right"]
        power_l = self.power_dict[self.level][self.assemble_method][str(self.main_lane_num)]["left"]
        if data.level in ["快速路", "主干路"] and self.main_lane_num == 10 and data.lightArmType == "单臂":
            power_r = 300
        poles_1 = {
            "materialCode": None,
            "category1": "道路灯具",
            "category2": "灯杆",
            "lightArmType": data.lightArmType,
            "location": light_locs_1,
            "lumen": None,
            "count": self.real_light_num,
            "angle": [0, 0, 0, 0, 0, 1],
            "elevationAngle": angle,
            "lightBulb": [{
                "materialCode": None,
                "power": power_r,
                "pos": "right"
            }]
        }
        
        poles_2 = {
            "materialCode": None,
            "category1": "道路灯具",
            "category2": "灯杆",
            "lightArmType": data.lightArmType,
            "location": light_locs_2,
            "lumen": None,
            "count": self.real_light_num,
            "angle": [0, 0, 0, 0, 0, 1],
            "elevationAngle": angle,
            "lightBulb": [{
                "materialCode": None,
                "power": power_r,
                "pos": "right"
            }]
        }

        if data.lightArmType in ["高低臂", "平行臂"]:
            poles_1["lightBulb"].append(
            {
                "materialCode": None,
                "power": power_l,
                "pos": "left"
            })
            poles_2["lightBulb"].append(
            {
                "materialCode": None,
                "power": power_l,
                "pos": "left"
            })
            lights_1_1 = {
                "materialCode": None,
                "category1": "道路灯具",
                "category2": "路灯",
                "location": light_locs_1,
                "power": power_r,
                "count": self.real_light_num,
                "pos": "right"
            }
            lights_1_2 = {
                "materialCode": None,
                "category1": "道路灯具",
                "category2": "路灯",
                "location": light_locs_1,
                "power": power_l,
                "count": self.real_light_num,
                "pos": "left"
            }
            lights_2_1 = {
                "materialCode": None,
                "category1": "道路灯具",
                "category2": "路灯",
                "location": light_locs_2,
                "power": power_r,
                "count": self.real_light_num,
                "pos": "right"
            }
            lights_2_2 = {
                "materialCode": None,
                "category1": "道路灯具",
                "category2": "路灯",
                "location": light_locs_2,
                "power": power_l,
                "count": self.real_light_num,
                "pos": "left"
            }

            planInfo = deepcopy(self.planInfo)
            planInfo["products"] = [poles_1, poles_2, lights_1_1, lights_1_2, lights_2_1, lights_2_2]
            planInfo["lightNum"] = self.real_light_num * 4
        
        else:
            lights_1 = {
                "materialCode": None,
                "category1": "道路灯具",
                "category2": "路灯",
                "location": light_locs_1,
                "power": power_r,
                "count": self.real_light_num,
                "pos": "right"
            }
            lights_2 = {
                "materialCode": None,
                "category1": "道路灯具",
                "category2": "路灯",
                "location": light_locs_2,
                "power": power_r,
                "count": self.real_light_num,
                "pos": "right"
            }

            planInfo = deepcopy(self.planInfo)
            planInfo["products"] = [poles_1, poles_2, lights_1, lights_2]
            planInfo["lightNum"] = self.real_light_num * 2

        return planInfo
    
    def design_double_inter_pole(self, roomList, data: Inputs) -> dict:
        """双侧交错布灯-仅高低臂、单臂"""

        # 两边绿化带取第1,2个
        if self.side_tree_num >= 2:
            for lane in roomList[0]["objects"]:
                if lane["type"] in ["tree", "concrete", "guardrail"] and len(lane["locations"]) >= 2:
                    light_x_1 = lane["locations"][0]["x"]
                    light_x_2 = lane["locations"][1]["x"]
                    key_road_w_1 = lane["locations"][0]["w"]
                    key_road_w_2 = lane["locations"][1]["w"]
                    if light_x_1 < self.road_w / 2:
                        light_x_1 = light_x_1 + key_road_w_1 / 2 - self.person_light_gap
                        light_x_2 = light_x_2 - key_road_w_2 / 2 + self.person_light_gap
                    else:
                        light_x_1 = light_x_1 - key_road_w_1 / 2 + self.person_light_gap
                        light_x_2 = light_x_2 + key_road_w_2 / 2 - self.person_light_gap
                    break
        # 放到人行道上
        elif self.person_lane_num == 2:
            for lane in roomList[0]["objects"]:
                if lane["type"] == "person_road":
                    light_x_1 = lane["locations"][0]["x"]
                    key_road_w_1 = lane["locations"][0]["w"]
                    light_x_2 = lane["locations"][1]["x"]
                    key_road_w_2 = lane["locations"][1]["w"]
                    if light_x_1 < self.road_w / 2:
                        light_x_1 = light_x_1 + key_road_w_1 / 2 - self.person_light_gap
                        light_x_2 = light_x_2 - key_road_w_2 / 2 + self.person_light_gap
                    else:
                        light_x_1 = light_x_1 - key_road_w_1 / 2 + self.person_light_gap
                        light_x_2 = light_x_2 + key_road_w_2 / 2 - self.person_light_gap
                    break
        # 主路边上
        else:
            for lane in roomList[0]["objects"]:
                if lane["type"] == "main_road":
                    if len(lane["locations"]) == 1:
                        key_road_w = lane["locations"][0]["w"]
                        light_x_1 = lane["locations"][0]["x"]
                        light_x_2 = lane["locations"][0]["x"]
                    else:
                        key_road_w = lane["locations"][0]["w"]
                        light_x_1 = lane["locations"][-2]["x"]
                        light_x_2 = lane["locations"][-1]["x"]
                            
            if light_x_1 < self.road_w / 2:
                light_x_1 -= key_road_w / 2
                light_x_2 += key_road_w / 2
            else:
                light_x_1 += key_road_w / 2
                light_x_2 -= key_road_w / 2

        r_z_1 = 0
        r_z_2 = 180
        if light_x_1 > self.road_w / 2:
            r_z_1 = 180
            r_z_2 = 0

        light_locs_1 = []
        for i in range(self.fake_light_num):
            light_locs_1.append({
                "x": light_x_1,
                "y": i * self.light_gap,
                "z": self.light_h / 2,
                "w": 1,
                "h": 1,
                "l": self.light_h,
                "rotation": [0, 0, r_z_1]
            })

        light_locs_2 = []
        for i in range(self.fake_light_num):
            light_locs_2.append({
                "x": light_x_2,
                "y": i * self.light_gap + self.light_gap / 2,
                "z": self.light_h / 2,
                "w": 1,
                "h": 1,
                "l": self.light_h,
                "rotation": [0, 0, r_z_2]
            })

        angle = self.__class__.angle_dict[str(self.main_lane_num)]
        power_r = self.power_dict[self.level][self.assemble_method][str(self.main_lane_num)]["right"]
        power_l = self.power_dict[self.level][self.assemble_method][str(self.main_lane_num)]["left"]
        if data.level in ["快速路", "主干路"] and self.main_lane_num == 10 and data.lightArmType == "单臂":
            power_r = 300
        poles_1 = {
            "materialCode": None,
            "category1": "道路灯具",
            "category2": "灯杆",
            "lightArmType": data.lightArmType,
            "location": light_locs_1,
            "lumen": None,
            "count": self.real_light_num,
            "angle": [0, 0, 0, 0, 0, 1],
            "elevationAngle": angle,
            "lightBulb": [{
                "materialCode": None,
                "power": power_r,
                "pos": "right"
            }]
        }
        
        poles_2 = {
            "materialCode": None,
            "category1": "道路灯具",
            "category2": "灯杆",
            "lightArmType": data.lightArmType,
            "location": light_locs_2,
            "lumen": None,
            "count": self.real_light_num,
            "angle": [0, 0, 0, 0, 0, 1],
            "elevationAngle": angle,
            "lightBulb": [{
                "materialCode": None,
                "power": power_r,
                "pos": "right"
            }]
        }
        if data.lightArmType in ["高低臂", "平行臂"]:
            poles_1["lightBulb"].append(
            {
                "materialCode": None,
                "power": power_l,
                "pos": "left"
            })
            poles_2["lightBulb"].append(
            {
                "materialCode": None,
                "power": power_l,
                "pos": "left"
            })
            lights_1_1 = {
                "materialCode": None,
                "category1": "道路灯具",
                "category2": "路灯",
                "location": light_locs_1,
                "power": power_r,
                "count": self.real_light_num,
                "pos": "right"
            }
            lights_1_2 = {
                "materialCode": None,
                "category1": "道路灯具",
                "category2": "路灯",
                "location": light_locs_1,
                "power": power_l,
                "count": self.real_light_num,
                "pos": "left"
            }
            lights_2_1 = {
                "materialCode": None,
                "category1": "道路灯具",
                "category2": "路灯",
                "location": light_locs_2,
                "power": power_r,
                "count": self.real_light_num,
                "pos": "right"
            }
            lights_2_2 = {
                "materialCode": None,
                "category1": "道路灯具",
                "category2": "路灯",
                "location": light_locs_2,
                "power": power_l,
                "count": self.real_light_num,
                "pos": "left"
            }

            planInfo = deepcopy(self.planInfo)
            planInfo["products"] = [poles_1, poles_2, lights_1_1, lights_1_2, lights_2_1, lights_2_2]
            planInfo["lightNum"] = self.real_light_num * 4
        else:
            lights_1 = {
                "materialCode": None,
                "category1": "道路灯具",
                "category2": "路灯",
                "location": light_locs_1,
                "power": power_r,
                "count": self.real_light_num,
                "pos": "right"
            }
            lights_2 = {
                "materialCode": None,
                "category1": "道路灯具",
                "category2": "路灯",
                "location": light_locs_2,
                "power": power_r,
                "count": self.real_light_num,
                "pos": "right"
            }

            planInfo = deepcopy(self.planInfo)
            planInfo["products"] = [poles_1, poles_2, lights_1, lights_2]
            planInfo["lightNum"] = self.real_light_num * 2

        return planInfo
    
    def add_sub_lights(self, roomList, planInfo, data: Inputs):
        """增加双侧对称的辅照明, 如果绿化带>=5放在绿化带上，其他布置在人行道上"""

        if self.side_tree_num >= 4:
            for lane in roomList[0]["objects"]:
                if lane["type"] in ["tree", "concrete", "guardrail"] and len(lane["locations"]) >= 4:
                    light_x_1 = lane["locations"][-2]["x"]
                    light_x_2 = lane["locations"][-1]["x"]
        elif self.person_lane_num == 2:
            for lane in roomList[0]["objects"]:
                if lane["type"] == "person_road":
                    light_x_1 = lane["locations"][0]["x"]
                    key_road_w_1 = lane["locations"][0]["w"]
                    light_x_2 = lane["locations"][1]["x"]
                    key_road_w_2 = lane["locations"][1]["w"]
                    if light_x_1 < self.road_w / 2:
                        light_x_1 = light_x_1 + key_road_w_1 / 2 - self.person_light_gap
                        light_x_2 = light_x_2 - key_road_w_2 / 2 + self.person_light_gap
                    else:
                        light_x_1 = light_x_1 - key_road_w_1 / 2 + self.person_light_gap
                        light_x_2 = light_x_2 + key_road_w_2 / 2 - self.person_light_gap
                    break
        else:
            return planInfo

        r_z_1 = 0
        r_z_2 = 180
        if light_x_1 > self.road_w / 2:
            r_z_1 = 180
            r_z_2 = 0

        light_locs_1 = []
        for i in range(self.fake_light_num):
            light_locs_1.append({
                "x": light_x_1,
                "y": i * self.light_gap,
                "z": self.light_h / 2,
                "w": 1,
                "h": 1,
                "l": self.light_h,
                "rotation": [0, 0, r_z_1]
            })

        light_locs_2 = []
        for i in range(self.fake_light_num):
            light_locs_2.append({
                "x": light_x_2,
                "y": i * self.light_gap,
                "z": self.light_h / 2,
                "w": 1,
                "h": 1,
                "l": self.light_h,
                "rotation": [0, 0, r_z_2]
            })

        angle = self.__class__.angle_dict[str(self.main_lane_num)]
        poles_1 = {
            "materialCode": None,
            "category1": "道路灯具",
            "category2": "灯杆",
            "lightArmType": data.subLightArmType,
            "location": light_locs_1,
            "lumen": None,
            "count": self.real_light_num,
            "angle": [0, 0, 0, 0, 0, 1],
            "elevationAngle": angle,
            "lightBulb": []
        }
        
        poles_2 = {
            "materialCode": None,
            "category1": "道路灯具",
            "category2": "灯杆",
            "lightArmType": data.subLightArmType,
            "location": light_locs_2,
            "lumen": None,
            "count": self.real_light_num,
            "angle": [0, 0, 0, 0, 0, 1],
            "elevationAngle": angle,
            "lightBulb": []
        }

        if data.subLightArmType == "高低臂":
            poles_1["lightBulb"] = [{
                "materialCode": None,
                "power": 100,
                "pos": "right"
            },
            {
                "materialCode": None,
                "power": 60,
                "pos": "left"
            }]
            poles_2["lightBulb"] = [{
                "materialCode": None,
                "power": 100,
                "pos": "right"
            },
            {
                "materialCode": None,
                "power": 60,
                "pos": "left"
            }]
            lights_1_1 = {
                "materialCode": None,
                "category1": "道路灯具",
                "category2": "路灯",
                "location": light_locs_1,
                "power": 100,
                "count": self.real_light_num,
                "pos": "right"
            }
            lights_1_2 = {
                "materialCode": None,
                "category1": "道路灯具",
                "category2": "路灯",
                "location": light_locs_1,
                "power": 60,
                "count": self.real_light_num,
                "pos": "left"
            }
            lights_2_1 = {
                "materialCode": None,
                "category1": "道路灯具",
                "category2": "路灯",
                "location": light_locs_2,
                "power": 100,
                "count": self.real_light_num,
                "pos": "right"
            }
            lights_2_2 = {
                "materialCode": None,
                "category1": "道路灯具",
                "category2": "路灯",
                "location": light_locs_2,
                "power": 60,
                "count": self.real_light_num,
                "pos": "left"
            }

            planInfo["products"].extend([poles_1, poles_2, lights_1_1, lights_1_2, lights_2_1, lights_2_2])
            planInfo["lightNum"] += self.real_light_num * 4
        # 单臂
        else:
            poles_1["lightBulb"] = [{
                "materialCode": None,
                "power": 60,
                "pos": "right"
            }]
            poles_2["lightBulb"] = [{
                "materialCode": None,
                "power": 60,
                "pos": "right"
            }]
            lights_1 = {
                "materialCode": None,
                "category1": "道路灯具",
                "category2": "路灯",
                "location": light_locs_1,
                "power": 60,
                "count": self.real_light_num,
                "pos": "right"
            }
            lights_2 = {
                "materialCode": None,
                "category1": "道路灯具",
                "category2": "路灯",
                "location": light_locs_2,
                "power": 60,
                "count": self.real_light_num,
                "pos": "right"
            }

            planInfo["products"].extend([poles_1, poles_2, lights_1, lights_2])
            planInfo["lightNum"] += self.real_light_num * 2

        return planInfo
    
    def add_platform(self, planInfo):
        """增加智能控制平台"""

        platform = {
            "materialCode": None,
            "category1": "道路灯具",
            "category2": "平台",
            "count": 1
        }
        planInfo["products"].append(platform)

        return planInfo