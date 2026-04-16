from apps.req.metro_agent_req import Inputs
from apps.metro_agent.asset_info import assets_info
from apps.metro_agent.layout_objects import layout_pillars_grid, layout_aligned_lights_and_cells


class ConstructMetro:
    def __init__(self):
        pass

    def build_metro(self, metro_data):
        # Implement the logic to construct metro plans based on metro_data
        roomList = []
        for data in metro_data:
            plan = {
                "station": data.get("station"),
                "line": data.get("line"),
                "arrival_time": data.get("arrival_time"),
                "departure_time": data.get("departure_time"),
            }
            roomList = []

        return roomList

    def build_customer_service(self, data: Inputs):
        """客服中心空间构建"""

        roomList = []
        roomInfo_1 = {
            "name": "客服中心",
            "rectangle": {
                "x_min": data.roomLength/2 - data.customerServiceLength/2,
                "y_min": data.roomWidth - data.outerPassWidth_2 - data.customerServiceWidth/2,
                "z_min": 0,
                "x_max": data.roomLength/2 + data.customerServiceLength/2,
                "y_max": data.roomWidth - data.outerPassWidth_2 + data.customerServiceWidth/2,
                "z_max": data.roomHeight
                },
            "objects": [
                {
                    "type": "客服中心",
                    "locations": [{
                        "x": data.roomLength / 2,
                        "y": data.roomWidth - data.outerPassWidth_2,
                        "z": 0,
                        "w": data.customerServiceWidth,
                        "h": data.customerServiceLength,
                        "l": data.roomHeight,
                        "rotation": [0, 0, 0]
                    }]
                }
            ]
        }
        roomList.append(roomInfo_1)

        return roomList

    def build_station_hall(self, data: Inputs):
        """站厅空间构建"""
        roomInfo_1 = {
            "name": "站厅外通道1",
            "rectangle": {
                "x_min": 0,
                "y_min": 0,
                "z_min": 0,
                "x_max": data.roomLength,
                "y_max": data.outerPassWidth_1,
                "z_max": data.roomHeight
                }
        }
        roomInfo_2 = {
            "name": "站厅外通道2",
            "rectangle": {
                "x_min": 0,
                "y_min": data.roomWidth - data.outerPassWidth_2,
                "z_min": 0,
                "x_max": data.roomLength,
                "y_max": data.roomWidth,
                "z_max": data.roomHeight
                }
        }
        margin = 9  # 站厅两侧预留空间
        innerPass = {
            "name": "站厅内通道",
            "rectangle": {
                "x_min": margin,
                "y_min": data.outerPassWidth_1,
                "z_min": 0,
                "x_max": data.roomLength-margin,
                "y_max": data.outerPassWidth_1 + data.innerPassWidth,
                "z_max": data.roomHeight
                }
        }
        # roomInfo_4 = self.build_customer_service(data)
        # roomList = [roomInfo_1, roomInfo_2, roomInfo_3]+roomInfo_4

        # add elevator
        elevator_info = assets_info["电梯"]
        elevator_location = {
            "x": (innerPass["rectangle"]["x_max"] + innerPass["rectangle"]["x_min"]) / 2, 
            "y": (innerPass["rectangle"]["y_max"] + innerPass["rectangle"]["y_min"]) / 2,
            "z": 0,
            "w": elevator_info["size"][0],
            "h": elevator_info["size"][1],
            "l": elevator_info["size"][2],
            "rotation": [0, 0, 0]
        }
        elevator_object = {
            "type": "电梯",
            "locations": [elevator_location]
        }
        innerPass["objects"] = [elevator_object]
        # add pillars to station hall
        # Calculate number of pillars along length
        y_max = innerPass["rectangle"]["y_max"] 
        y_min = innerPass["rectangle"]["y_min"] 
        x_min = 0
        x_max = data.roomLength
        pillars = layout_pillars_grid(
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
            spacing=8
        )
        pillar_object = {
            "type": "立柱",
            "locations": pillars
        }
        w,h,l = assets_info["立柱"]["size"]
        for pillar in pillar_object["locations"]:
            pillar["w"] = w
            pillar["h"] = h
            pillar["l"] = l
        innerPass["objects"].append(pillar_object)
        center_x, center_y = (x_min + x_max)/2, (y_min + y_max)/2

        # add 扶梯
        escalator_info = assets_info["扶梯"]
        left_escalator = {
            "x": center_x - 10 - escalator_info["size"][0]/2,
            "y": center_y,
            "z": 0,
            "w": escalator_info["size"][0],
            "h": escalator_info["size"][1],
            "l": escalator_info["size"][2],
            "rotation": [0, 0, 0]
        }
        right_escalator= {
            "x": center_x + 10 + escalator_info["size"][0]/2,
            "y": center_y,
            "z": 0,
            "w": escalator_info["size"][0],
            "h": escalator_info["size"][1],
            "l": escalator_info["size"][2],
            "rotation": [0, 0, 180]
        }
        escalator_object = {
            "type": "扶梯",
            "locations": [left_escalator, right_escalator]
        }
        innerPass["objects"].append(escalator_object)

        # 客服中心
        customer_center_location = {
            "x": center_x,
            "y": y_max-data.customerServiceWidth/2,
            "z": 0,
            "w": data.customerServiceLength,
            "h": data.customerServiceWidth,
            "l": data.roomHeight,
            "rotation": [0, 0, 0],
        }
        customer_center_object = {
            "type": "客服中心",
            "locations": [customer_center_location]
        }
        # 客服中心计算边界, 外扩3
        margin = 3
        c_x_min = customer_center_location["x"] - data.customerServiceLength/2 - margin
        c_x_max = customer_center_location["x"] + data.customerServiceLength/2 + margin
        c_y_min = customer_center_location["y"] - data.customerServiceWidth/2 - margin
        c_y_max = customer_center_location["y"] + data.customerServiceWidth/2 + margin
        roomInfo_4 = {
            "name": "客服中心",
            "rectangle": {
                "x_min": c_x_min,
                "y_min": c_y_min,
                "z_min": 0,
                "x_max": c_x_max,
                "y_max": c_y_max,
                "z_max": data.roomHeight
                }
        }

        innerPass["objects"].append(customer_center_object)
        # 添加闸机， 安检区域
        if data.outerPassWidth_1 > 0:
            turnstile_info = assets_info["闸机区域（双通道）"]
            security_info = assets_info["安检区域（双通道）"]
        else:
            turnstile_info = assets_info["闸机区域（单通道）"]
            security_info = assets_info["安检区域（单通道）"]
        # 闸机
        turnstile_offset = 33
        turnstile_left = {
            "x": center_x - turnstile_offset,
            "y": y_max,
            "z": 0,
            "w": turnstile_info["size"][0],
            "h": turnstile_info["size"][1],
            "l": turnstile_info["size"][2],
            "rotation": [0, 0, 0]
        }
        turnstile_right = {
            "x": center_x + turnstile_offset,
            "y": y_min,
            "z": 0,
            "w": turnstile_info["size"][0],
            "h": turnstile_info["size"][1],
            "l": turnstile_info["size"][2],
            "rotation": [0, 0, 180]
        }
        turnstile_object = {
            "type": "闸机",
            "locations": [turnstile_left, turnstile_right]
        }
        innerPass["objects"].append(turnstile_object)
        # 添加安检区域
        se_offset = turnstile_offset + 3 + security_info["size"][0] / 2
        security_left = {
            "x": center_x - se_offset,
            "y": center_y,
            "z": 0,
            "w": security_info["size"][0],
            "h": security_info["size"][1],
            "l": security_info["size"][2],
            "rotation": [0, 0, 0] 
        }
        security_right = {
            "x": center_x + se_offset,
            "y": center_y,
            "z": 0,
            "w": security_info["size"][0],
            "h": security_info["size"][1],
            "l": security_info["size"][2],
            "rotation": [0, 0, 180] 
        }
        security_object = {
            "type": "安检区域",
            "locations": [security_left, security_right]
        }
        innerPass["objects"].append(security_object) 
        innerPass["rectangle"]["x_min"] = security_left["x"]
        innerPass["rectangle"]["x_max"] = security_right["x"]
        # add 综合信息
        general_info = assets_info["综合信息"]
        left_general_upper = {
            "x": turnstile_left["x"],
            "y": data.roomWidth,
            "z": 1.5,
            "w": general_info["size"][0],
            "h": general_info["size"][1],
            "l": general_info["size"][2],
            "rotation": [0, 0, 0],
        }
        right_general_upper = {
            "x": turnstile_right["x"],
            "y": data.roomWidth,
            "z": 1.5,
            "w": general_info["size"][0],
            "h": general_info["size"][1],
            "l": general_info["size"][2],
            "rotation": [0, 0, 0]
        }
        left_general_lower = {
            "x": turnstile_left["x"],
            "y": 0,
            "z": 1.5,
            "w": general_info["size"][0],
            "h": general_info["size"][1],
            "l": general_info["size"][2],
            "rotation": [0, 0, 180]
        }
        right_general_lower = {
            "x": turnstile_right["x"],
            "y": 0,
            "z": 1.5,
            "w": general_info["size"][0],
            "h": general_info["size"][1],
            "l": general_info["size"][2],
            "rotation": [0, 0, 180]
        }
        general_infos = [
            left_general_upper,
            right_general_upper,
            left_general_lower,
            right_general_lower,
        ]
        general_objects = {
            "type": "综合信息",
            "locations": general_infos
        }
        innerPass["objects"].append(general_objects)

        # 广告牌
        ad_info = assets_info["广告牌"]
        ad_left_upper = {
            "x": center_x - 8,
            "y": data.roomWidth,
            "z": 1.57,
            "w": ad_info["size"][0],
            "h": ad_info["size"][1],
            "l": ad_info["size"][2],
            "rotation": [0, 0, 0]
        }
        ad_right_upper = {
            "x": center_x + 8,
            "y": data.roomWidth,
            "z": 1.57,
            "w": ad_info["size"][0],
            "h": ad_info["size"][1],
            "l": ad_info["size"][2],
            "rotation": [0, 0, 0]
        }
        ad_left_lower = {
            "x": center_x - 8,
            "y": 0,
            "z": 1.57,
            "w": ad_info["size"][0],
            "h": ad_info["size"][1],
            "l": ad_info["size"][2],
            "rotation": [0, 0, 180]
        }
        ad_right_lower = {
            "x": center_x + 8,
            "y": 0,
            "z": 1.57,
            "w": ad_info["size"][0],
            "h": ad_info["size"][1],    
            "l": ad_info["size"][2],
            "rotation": [0, 0, 180]
        }
        ad_objects = {
            "type": "广告牌",
            "locations": [
                ad_left_upper,
                ad_right_upper,
                ad_left_lower,
                ad_right_lower,
            ]
        }
        innerPass["objects"].append(ad_objects)
        # Fire hydrant
        fire_hydrant_info = assets_info["消防栓"]
        fh_left_upper = {
            "x": center_x - 12,
            "y": data.roomWidth,
            "z": 0,
            "w": fire_hydrant_info["size"][0],
            "h": fire_hydrant_info["size"][1],
            "l": fire_hydrant_info["size"][2],
            "rotation": [0, 0, 0]
        }
        fh_right_upper = {
            "x": center_x + 12,
            "y": data.roomWidth,
            "z": 0,
            "w": fire_hydrant_info["size"][0],
            "h": fire_hydrant_info["size"][1],
            "l": fire_hydrant_info["size"][2],
            "rotation": [0, 0, 0]
        }
        fh_left_lower = {
            "x": center_x - 12,
            "y": 0,
            "z": 0,
            "w": fire_hydrant_info["size"][0],
            "h": fire_hydrant_info["size"][1],
            "l": fire_hydrant_info["size"][2],
            "rotation": [0, 0, 180]
        }
        fh_right_lower = {
            "x": center_x + 12,
            "y": 0,
            "z": 0,
            "w": fire_hydrant_info["size"][0],
            "h": fire_hydrant_info["size"][1],
            "l": fire_hydrant_info["size"][2],
            "rotation": [0, 0, 180]
        }
        fh_objects = {
            "type": "fireHydrant",
            "locations": [
                fh_left_upper,
                fh_right_upper,
                fh_left_lower,
                fh_right_lower,
            ]
        }
        innerPass["objects"].append(fh_objects)

        roomList = [roomInfo_1, roomInfo_2, innerPass, roomInfo_4]
        return roomList

    def build_platform(self, data: Inputs):
        """站台空间构建"""
        # 站台
        platform = {
            "name": "站台",
            "rectangle": {
                "x_min": 0,
                "y_min": 0,
                "z_min": 0,
                "x_max": data.roomLength,
                "y_max": data.roomWidth,
                "z_max": data.roomHeight
                }
        }
        # 下过道 # y轴方向，较小的一边
        outer_pass_1 = {
            "name": "站台下过道",
            "rectangle": {
                "x_min": 0,
                "y_min": 0,
                "z_min": 0,
                "x_max": data.roomLength,
                "y_max": data.outerPassWidth_1,
                "z_max": data.roomHeight
            }
        }
        # 候车区
        waiting_area = {
            "name": "站台候车区",
            "rectangle": {
                "x_min": 0,
                "y_min": data.outerPassWidth_1,
                "z_min": 0,
                "x_max": data.roomLength,
                "y_max": data.outerPassWidth_1+data.innerPassWidth,
                "z_max": data.roomHeight
            }
        }
        # ensure objects list exists before appending objects (e.g., 扶梯)
        waiting_area["objects"] = []
        # add escalator
        center_x, center_y = data.roomLength/2, data.innerPassWidth/2+data.outerPassWidth_1,
        escalator_info = assets_info["扶梯"]
        left_escalator = {
            "x": center_x - 10 - escalator_info["size"][0]/2,
            "y": center_y,
            "z": 0,
            "w": escalator_info["size"][0],
            "h": escalator_info["size"][1],
            "l": escalator_info["size"][2],
            "rotation": [0, 0, 0]
        }
        right_escalator = {
            "x": center_x + 10 + escalator_info["size"][0] / 2,
            "y": center_y,
            "z": 0,
            "w": escalator_info["size"][0],
            "h": escalator_info["size"][1],
            "l": escalator_info["size"][2],
            "rotation": [0, 0, 180],
        }
        escalator_object = {
            "type": "扶梯",
            "locations": [left_escalator, right_escalator]
        }
        waiting_area["objects"].append(escalator_object)

        # 上过道
        outer_pass_2 = {
            "name": "站台上过道",
            "rectangle": {
                "x_min": 0,
                "y_min": data.roomWidth - data.outerPassWidth_2,
                "z_min": 0,
                "x_max": data.roomLength,
                "y_max": data.roomWidth,
                "z_max": data.roomHeight
            }
        }
        room_list = [platform, outer_pass_1, waiting_area, outer_pass_2]
        return room_list

    def build_control_room(self, data: Inputs):
        """控制室空间构建"""
        roomInfo_1 = {
            "name": "控制室",
            "rectangle": {
                "x_min": 0,
                "y_min": 0,
                "z_min": 0,
                "x_max": data.roomLength,
                "y_max": data.roomWidth,
                "z_max": data.roomHeight
                }
        }
        roomList = [roomInfo_1]
        return roomList
# preview

if __name__ == "__main__":
    print("Construct Metro Plan Preview")
    print("=" * 60)
    # Define station hall parameters
    data = Inputs(
        roomLength=120,
        # roomWidth=33,
        roomHeight=6,
        outerPassWidth_1=3,
        outerPassWidth_2=3,
        innerPassWidth=30,  
        customerServiceLength=3.6,
        customerServiceWidth=2.5,
        roomType="站厅",
    )
    constructor = ConstructMetro()
    station_hall_rooms = constructor.build_station_hall(data)
    # save json file
    import json
    with open("station_hall_rooms.json", "w", encoding="utf-8") as f:
        json.dump(station_hall_rooms, f, ensure_ascii=False, indent=4)
    print("Station hall rooms saved to station_hall_rooms.json")
