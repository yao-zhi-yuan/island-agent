import random
from apps.req.road_agent_req import Inputs


class ConstructRoad:

    def __init__(self):
        self.line_width = 0.15
        self.dashed_line_len = 2
        self.dashed_line_gap = 4
        self.line_edge_gap = 0.1


    def build_road(self, data: Inputs):

        road_w = 0
        sub_num = 0
        bike_num = 0
        person_num = 0

        mid_split_type = "tree"
        mid_split_num = 0
        mid_split_w = 1

        side_split_type = ""
        side_split_num = 0
        side_split_w = 0

        for lane in data.lanes:
            if lane.type == "机动车道":
                lane_num = lane.count
                lane_width = lane.width
                road_w += lane_num * lane_width
            elif lane.type == "辅道":
                sub_num = lane.count
                sub_width = lane.width
                road_w += sub_num * sub_width
            elif lane.type == "非机动车道":
                bike_num = lane.count
                bike_width = lane.width
                road_w += bike_num * bike_width
            elif lane.type == "人行道":
                person_num = lane.count
                person_width = lane.width
                road_w += person_num * person_width
            elif lane.type == "绿化带":
                if lane.count == 1:
                    mid_split_type = "tree"
                    mid_split_num = lane.count
                    mid_split_w = lane.width
                else:
                    side_split_type = "tree"
                    side_split_num = lane.count
                    side_split_w = lane.width
                road_w += lane.count * lane.count
            elif lane.type == "水泥墩" and data.level == "快速路":
                if lane.count == 1:
                    mid_split_type = "guardrail"
                    mid_split_num = lane.count
                    mid_split_w = lane.width
                else:
                    side_split_type = "guardrail"
                    side_split_num = lane.count
                    side_split_w = lane.width
                road_w += lane.count * lane.width
            elif lane.type == "水泥墩" and data.level != "快速路":
                if lane.count == 1:
                    mid_split_type = "concrete"
                    mid_split_num = lane.count
                    mid_split_w = lane.width
                else:
                    side_split_type = "concrete"
                    side_split_num = lane.count
                    side_split_w = lane.width
                road_w += lane.count * lane.width

        max_len = 200

        mid_split_locs = []
        # 加中间绿化带
        if data.assembleMethod == "中心对称" or mid_split_num == 1:
            road_w += mid_split_w
            start_x = mid_split_w / 2
            mid_split_locs.append({
                "x": road_w / 2,
                "y": max_len / 2,
                "z": 0,
                "w": mid_split_w,
                "h": max_len,
                "l": 0,
                "rotation": [0, 0, 0]
            })
        else:
            start_x = 0
        
        # 主路
        main_road_locs = []
        l_start = 0
        r_start = 0
        if lane_num == 1:
            l_start = road_w / 2 - lane_width / 2
            r_start = road_w / 2 + lane_width / 2
            main_road_locs.append({
                "x": road_w / 2,
                "y": max_len / 2,
                "z": 0,
                "w": lane_width,
                "h": max_len,
                "l": 0,
                "rotation": [0, 0, 0]
            })
        else:
            for i in range(int(lane_num / 2)):
                x1 = road_w / 2 - start_x - lane_width / 2 * (2 * i + 1)
                x2 = road_w / 2 + start_x + lane_width / 2 * (2 * i + 1)
                l_start = x1 - lane_width / 2
                r_start = x2 + lane_width / 2
                main_road_locs.append({
                    "x": x1,
                    "y": max_len / 2,
                    "z": 0,
                    "w": lane_width,
                    "h": max_len,
                    "l": 0,
                    "rotation": [0, 0, 0]
                })
                main_road_locs.append({
                    "x": x2,
                    "y": max_len / 2,
                    "z": 0,
                    "w": lane_width,
                    "h": max_len,
                    "l": 0,
                    "rotation": [0, 0, 0]
                })
        
        # 绿化带2
        side_split_locs = []
        if side_split_num >= 2:
            side_split_locs.extend([{
                "x": road_w / 2 - start_x - lane_width * lane_num / 2 - side_split_w / 2,
                "y": max_len / 2,
                "z": 0,
                "w": side_split_w,
                "h": max_len,
                "l": 0,
                "rotation": [0, 0, 0]
            },{
                "x": road_w / 2 + start_x + lane_width * lane_num / 2 + side_split_w / 2,
                "y": max_len / 2,
                "z": 0,
                "w": side_split_w,
                "h": max_len,
                "l": 0,
                "rotation": [0, 0, 0]
            }])
            l_start = road_w / 2 - start_x - lane_width * lane_num / 2 - side_split_w
            r_start = road_w / 2 + start_x + lane_width * lane_num / 2 + side_split_w

        # 辅路
        sub_road_locs = []
        for i in range(int(sub_num / 2)):
            sub_road_locs.append({
                "x": l_start - sub_width / 2,
                "y": max_len / 2,
                "z": 0,
                "w": sub_width,
                "h": max_len,
                "l": 0,
                "rotation": [0, 0, 0]
            })
            sub_road_locs.append({
                "x": r_start + sub_width / 2,
                "y": max_len / 2,
                "z": 0,
                "w": sub_width,
                "h": max_len,
                "l": 0,
                "rotation": [0, 0, 0]
            })
            l_start -= sub_width
            r_start += sub_width

        # 非机动车道道
        bike_road_locs = []
        for i in range (bike_num):
            symbol = -1 if i % 2 else 1
            if symbol == -1:
                x = l_start - bike_width / 2
                l_start = x - bike_width / 2
            else:
                x = r_start + bike_width / 2
                r_start = x + bike_width / 2
            
            bike_road_locs.append({
                "x": x,
                "y": max_len / 2,
                "z": 0,
                "w": bike_width,
                "h": max_len,
                "l": 0,
                "rotation": [0, 0, 0]
            })
            
        # 绿化带3
        if side_split_num >= 4:
            side_split_locs.extend([{
                "x": l_start - side_split_w / 2,
                "y": max_len / 2,
                "z": 0,
                "w": side_split_w,
                "h": max_len,
                "l": 0,
                "rotation": [0, 0, 0]
            },{
                "x": r_start + side_split_w / 2,
                "y": max_len / 2,
                "z": 0,
                "w": side_split_w,
                "h": max_len,
                "l": 0,
                "rotation": [0, 0, 0]
            }])
            l_start -= side_split_w
            r_start += side_split_w

        # 人行道
        person_road_locs = []
        for i in range (person_num):
            symbol = -1 if i % 2 else 1
            if symbol == 1:
                x = l_start - person_width / 2
                l_start = x - person_width / 2
            else:
                x = r_start + person_width / 2
                r_start = x + person_width / 2
            person_road_locs.append({
                "x": x,
                "y": max_len / 2,
                "z": 0,
                "w": person_width,
                "h": max_len,
                "l": 0,
                "rotation": [0, 0, 0]
            })

        roomList = []
        roomInfo_1 = {
            "name": data.level,
            "rectangle": {
                "x_min": 0,
                "y_min": 0,
                "z_min": 0,
                "x_max": road_w,
                "y_max": max_len,
                "z_max": 0
                },
            "objects": [
                {
                    "type": "main_road",
                    "locations": main_road_locs
                }
            ]
        }

        if sub_num > 0:
            roomInfo_1["objects"].append({
                "type": "sub_road",
                "locations": sub_road_locs
            })

        if bike_num > 0:
            roomInfo_1["objects"].append({
                "type": "bike_road",
                "locations": bike_road_locs
            })

        if person_num > 0:
            roomInfo_1["objects"].append({
                "type": "person_road",
                "locations": person_road_locs
            })

        if mid_split_locs:
            roomInfo_1["objects"].append({
                "type": mid_split_type,
                "locations": mid_split_locs
            })
        if side_split_locs:
            roomInfo_1["objects"].append({
                "type": side_split_type,
                "locations": side_split_locs
            })

        roomList = [roomInfo_1]

        return roomList
    
    def draw_main_lines(self, roomList):
        """主干路车道线"""

        mid_type = "white_line"
        split_count = 0
        for lane in roomList[0]["objects"]:
            if lane["type"] in ["tree", "concrete", "guardrail"]:
                split_count += len(lane["locations"])
        if split_count % 2 == 0:
            mid_type = "yellow_line"

        main_lane_locs = []
        for lane in roomList[0]["objects"]:
            if lane["type"] == "main_road":
                main_lane_locs = lane["locations"]

        sub_lane_locs = []
        for lane in roomList[0]["objects"]:
            if lane["type"] == "sub_road":
                sub_lane_locs = lane["locations"]

        white_line_loc = []
        yellow_line_loc = []
        # 两车道中间是黄虚线
        if len(main_lane_locs) == 2 and split_count % 2 == 0:
            dashed_line_num = int(main_lane_locs[0]["h"] / (self.dashed_line_len + self.dashed_line_gap)) + 1
            for i in range(dashed_line_num):
                cur_loc = {
                    "x": main_lane_locs[0]["x"] + main_lane_locs[0]["w"] / 2,
                    "y": i * (self.dashed_line_len + self.dashed_line_gap),
                    "z": main_lane_locs[0]["z"],
                    "w": self.line_width,
                    "h": self.dashed_line_len,
                    "l": 0,
                    "rotation": [0, 0, 0]
                }
                yellow_line_loc.append(cur_loc)
        else:
            for idx, main_lane in enumerate(main_lane_locs):
                if idx == 0:
                    cur_loc = {
                            "x": main_lane["x"] + main_lane["w"] / 2 - self.line_edge_gap - self.line_width / 2,
                            "y": main_lane["y"],
                            "z": main_lane["z"],
                            "w": self.line_width,
                            "h": main_lane["h"],
                            "l": 0,
                            "rotation": [0, 0, 0]
                    }
                    if mid_type == "white_line":
                        white_line_loc.append(cur_loc)
                    else:
                        yellow_line_loc.append(cur_loc)
                elif idx == 1:
                    cur_loc = {
                            "x": main_lane["x"] - main_lane["w"] / 2 + self.line_edge_gap + self.line_width / 2,
                            "y": main_lane["y"],
                            "z": main_lane["z"],
                            "w": self.line_width,
                            "h": main_lane["h"],
                            "l": 0,
                            "rotation": [0, 0, 0]
                    }
                    if mid_type == "white_line":
                        white_line_loc.append(cur_loc)
                    else:
                        yellow_line_loc.append(cur_loc)
                elif idx % 2 == 0:
                    dashed_line_num = int(main_lane["h"] / (self.dashed_line_len + self.dashed_line_gap)) + 1
                    for i in range(dashed_line_num):
                        cur_loc = {
                            "x": main_lane["x"] + main_lane["w"] / 2,
                            "y": i * (self.dashed_line_len + self.dashed_line_gap),
                            "z": main_lane["z"],
                            "w": self.line_width,
                            "h": self.dashed_line_len,
                            "l": 0,
                            "rotation": [0, 0, 0]
                        }
                        white_line_loc.append(cur_loc)
                else:
                    dashed_line_num = int(main_lane["h"] / (self.dashed_line_len + self.dashed_line_gap)) + 1
                    for i in range(dashed_line_num):
                        cur_loc = {
                            "x": main_lane["x"] - main_lane["w"] / 2,
                            "y": i * (self.dashed_line_len + self.dashed_line_gap),
                            "z": main_lane["z"],
                            "w": self.line_width,
                            "h": self.dashed_line_len,
                            "l": 0,
                            "rotation": [0, 0, 0]
                        }
                        white_line_loc.append(cur_loc)

        # 有辅路和 2 条绿化带以上时
        if sub_lane_locs:
            if split_count >= 2:
                white_line_loc.append({
                    "x": main_lane_locs[-2]["x"] - main_lane_locs[-2]["w"] / 2 + self.line_edge_gap + self.line_width / 2,
                    "y": main_lane_locs[-2]["y"],
                    "z": main_lane_locs[-2]["z"],
                    "w": self.line_width,
                    "h": main_lane_locs[-2]["h"],
                    "l": 0,
                    "rotation": [0, 0, 0]
                })
                white_line_loc.append({
                    "x": main_lane_locs[-1]["x"] + main_lane_locs[-1]["w"] / 2 - self.line_edge_gap - self.line_width / 2,
                    "y": main_lane_locs[-1]["y"],
                    "z": main_lane_locs[-1]["z"],
                    "w": self.line_width,
                    "h": main_lane_locs[-1]["h"],
                    "l": 0,
                    "rotation": [0, 0, 0]
                })

        # 有辅路和 2 条绿化带以上时
        if sub_lane_locs:
            if split_count >= 2:
                sub_color = "white_line"
            else:
                sub_color = "yellow_line"
            for i, sub_lane in enumerate(sub_lane_locs):
                if i == 0:
                    cur_loc = {
                        "x": sub_lane["x"] + sub_lane["w"] / 2,
                        "y": sub_lane["y"],
                        "z": sub_lane["z"],
                        "w": self.line_width,
                        "h": sub_lane["h"],
                        "l": 0,
                        "rotation": [0, 0, 0]
                    }
                    cur_locs = eval(f"{sub_color}_loc")
                    cur_locs.append(cur_loc)
                elif i == 1:
                    cur_loc = {
                        "x": sub_lane["x"] - sub_lane["w"] / 2,
                        "y": sub_lane["y"],
                        "z": sub_lane["z"],
                        "w": self.line_width,
                        "h": sub_lane["h"],
                        "l": 0,
                        "rotation": [0, 0, 0]
                    }
                    cur_locs = eval(f"{sub_color}_loc")
                    cur_locs.append(cur_loc)
                
        if len(sub_lane_locs) in [2, 4]:
            yellow_line_loc.append({
                "x": sub_lane_locs[-2]["x"] - sub_lane_locs[-2]["w"] / 2 + self.line_edge_gap + self.line_width / 2,
                "y": sub_lane_locs[-2]["y"],
                "z": sub_lane_locs[-2]["z"],
                "w": self.line_width,
                "h": sub_lane_locs[-2]["h"],
                "l": 0,
                "rotation": [0, 0, 0]
            })
            yellow_line_loc.append({
                "x": sub_lane_locs[-1]["x"] + sub_lane_locs[-1]["w"] / 2 - self.line_edge_gap - self.line_width / 2,
                "y": sub_lane_locs[-1]["y"],
                "z": sub_lane_locs[-1]["z"],
                "w": self.line_width,
                "h": sub_lane_locs[-1]["h"],
                "l": 0,
                "rotation": [0, 0, 0]
            })

        if len(sub_lane_locs) == 4:
            dashed_line_num = int(sub_lane_locs[0]["h"] / (self.dashed_line_len + self.dashed_line_gap)) + 1
            for i in range(dashed_line_num):
                white_line_loc.append({
                    "x": sub_lane_locs[0]["x"] - sub_lane_locs[0]["w"] / 2,
                    "y": i * (self.dashed_line_len + self.dashed_line_gap),
                    "z": sub_lane_locs[0]["z"],
                    "w": self.line_width,
                    "h": self.dashed_line_len,
                    "l": 0,
                    "rotation": [0, 0, 0]
                })
                white_line_loc.append({
                    "x": sub_lane_locs[1]["x"] + sub_lane_locs[1]["w"] / 2,
                    "y": i * (self.dashed_line_len + self.dashed_line_gap),
                    "z": sub_lane_locs[1]["z"],
                    "w": self.line_width,
                    "h": self.dashed_line_len,
                    "l": 0,
                    "rotation": [0, 0, 0]
                })

        if not sub_lane_locs:
            yellow_line_loc.append({
                "x": main_lane_locs[-2]["x"] - main_lane_locs[-2]["w"] / 2 + self.line_edge_gap + self.line_width / 2,
                "y": main_lane_locs[-2]["y"],
                "z": main_lane_locs[-2]["z"],
                "w": self.line_width,
                "h": main_lane_locs[-2]["h"],
                "l": 0,
                "rotation": [0, 0, 0]
            })
            yellow_line_loc.append({
                "x": main_lane_locs[-1]["x"] + main_lane_locs[-1]["w"] / 2 - self.line_edge_gap - self.line_width / 2,
                "y": main_lane_locs[-1]["y"],
                "z": main_lane_locs[-1]["z"],
                "w": self.line_width,
                "h": main_lane_locs[-1]["h"],
                "l": 0,
                "rotation": [0, 0, 0]
            })

        if white_line_loc:
            roomList[0]["objects"].append({
                "type": "white_line",
                "locations": white_line_loc
            })
        if yellow_line_loc:
            roomList[0]["objects"].append({
                "type": "yellow_line",
                "locations": yellow_line_loc
            })
        
        return roomList
            
    def draw_single_lines(self, roomList):
        
        main_lane_locs = []
        yellow_line_loc = []
        for lane in roomList[0]["objects"]:
            if lane["type"] == "main_road":
                main_lane_locs = lane["locations"]
        
        white_line_loc = []
        if len(main_lane_locs) == 1:
            white_line_loc.append({
                "x": main_lane_locs[0]["x"] + main_lane_locs[0]["w"] / 2 - self.line_edge_gap - self.line_width / 2,
                "y": main_lane_locs[0]["y"],
                "z": main_lane_locs[0]["z"],
                "w": self.line_width,
                "h": main_lane_locs[0]["h"],
                "l": 0,
                "rotation": [0, 0, 0]
            })
            white_line_loc.append({
                "x": main_lane_locs[0]["x"] - main_lane_locs[0]["w"] / 2 + self.line_edge_gap + self.line_width / 2,
                "y": main_lane_locs[0]["y"],
                "z": main_lane_locs[0]["z"],
                "w": self.line_width,
                "h": main_lane_locs[0]["h"],
                "l": 0,
                "rotation": [0, 0, 0]
            })

        elif len(main_lane_locs) == 2:
            dashed_line_num = int(main_lane_locs[0]["h"] / (self.dashed_line_len + self.dashed_line_gap)) + 1
            for i in range(dashed_line_num):
                cur_loc = {
                    "x": main_lane_locs[0]["x"] + main_lane_locs[0]["w"] / 2,
                    "y": i * (self.dashed_line_len + self.dashed_line_gap),
                    "z": main_lane_locs[0]["z"],
                    "w": self.line_width,
                    "h": self.dashed_line_len,
                    "l": 0,
                    "rotation": [0, 0, 0]
                }
                yellow_line_loc.append(cur_loc)

            white_line_loc.append({
                "x": main_lane_locs[-2]["x"] - main_lane_locs[-2]["w"] / 2 + self.line_edge_gap + self.line_width / 2,
                "y": main_lane_locs[-2]["y"],
                "z": main_lane_locs[-2]["z"],
                "w": self.line_width,
                "h": main_lane_locs[-2]["h"],
                "l": 0,
                "rotation": [0, 0, 0]
            })
            white_line_loc.append({
                "x": main_lane_locs[-1]["x"] + main_lane_locs[-1]["w"] / 2 - self.line_edge_gap - self.line_width / 2,
                "y": main_lane_locs[-1]["y"],
                "z": main_lane_locs[-1]["z"],
                "w": self.line_width,
                "h": main_lane_locs[-1]["h"],
                "l": 0,
                "rotation": [0, 0, 0]
            })

        if white_line_loc:
            roomList[0]["objects"].append({
                "type": "white_line",
                "locations": white_line_loc
            })
        if yellow_line_loc:
            roomList[0]["objects"].append({
                "type": "yellow_line",
                "locations": yellow_line_loc
            })
        
        return roomList
    
    def add_cars(self, roomList):
        """添加车辆"""

        main_lane_locs = []
        for lane in roomList[0]["objects"]:
            if lane["type"] == "main_road":
                main_lane_locs = lane["locations"]
        
        for i in range(len(main_lane_locs)):

            x = main_lane_locs[i]["x"]
            y = random.randint(20, 100)
            if i % 2 == 0:
                rotation = [0, 0, 0]
            else:
                rotation = [0, 0, 180]
            
            roomList[0]["objects"].append({
                "type": "car",
                "locations": [{
                    "x": x,
                    "y": y,
                    "z": main_lane_locs[i]["z"],
                    "w": 1.8,
                    "h": 4.5,
                    "l": 0,
                    "rotation": rotation
                }]
            })
        
        return roomList