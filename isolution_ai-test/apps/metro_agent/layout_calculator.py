"""Metro lighting layout calculator.

This module calculates the number and positions of lighting fixtures
based on corridor dimensions and design schemes.
"""

import math
from typing import Dict


class MetroLayoutCalculator:
    """Calculate lighting fixture layouts for metro stations."""

    def __init__(self):
        # Layout parameters
        self.fixture_spacing = 3.0  # meters between fixtures
        self.min_corridor_width = 4.0  # minimum width for 1 row
        self.width_increment = 3.0  # add 1 row per 3m width

    def calculate_corridor_layout(
        self,
        length: float,
        width: float,
        scheme: str = "scheme1"
    ) -> Dict:
        """Calculate fixture layout for a corridor.

        Args:
            length: Corridor length in meters
            width: Corridor width in meters
            scheme: Design scheme ("scheme1" or "scheme2")

        Returns:
            dict with fixture counts and positions
        """
        if scheme == "scheme1":
            return self._calculate_scheme1_layout(length, width)
        elif scheme == "scheme2":
            return self._calculate_scheme2_layout(length, width)
        else:
            raise ValueError(f"Unknown scheme: {scheme}")

    def _calculate_scheme1_layout(
        self,
        length: float,
        width: float
    ) -> Dict:
        """Calculate Scheme 1 layout (linear only).

        Rules:
        - Width <= 4m: 1 row of linear fixtures
        - Every +3m width: +1 row

        Args:
            length: Corridor length in meters
            width: Corridor width in meters

        Returns:
            dict with counts and positions
        """
        # Calculate number of rows based on width
        num_rows = 1 + int((width - self.min_corridor_width) /
                           self.width_increment)
        num_rows = max(1, num_rows)

        # Calculate fixtures per row
        # Each linear fixture is 1.2m, with 3m spacing
        num_fixtures_per_row = math.ceil(length / self.fixture_spacing)

        # Total linear fixtures
        total_linear = num_rows * num_fixtures_per_row

        # Generate positions
        linear_positions = []
        row_spacing = width / (num_rows + 1)

        for row in range(num_rows):
            y_pos = row_spacing * (row + 1)
            for i in range(num_fixtures_per_row):
                x_pos = i * self.fixture_spacing
                linear_positions.append({
                    "x": x_pos,
                    "y": y_pos,
                    "type": "linear",
                    "series": "朗型",
                    "power": 40,
                    "row": row + 1
                })

        return {
            "scheme": "scheme1",
            "corridor_length": length,
            "corridor_width": width,
            "num_rows": num_rows,
            "linear_count": total_linear,
            "downlight_count": 0,
            "positions": linear_positions,
            "summary": (
                f"方案1: {num_rows}排线形灯，"
                f"共{total_linear}个朗型40W线形灯"
            )
        }

    def _calculate_scheme2_layout(
        self,
        length: float,
        width: float
    ) -> Dict:
        """Calculate Scheme 2 layout (linear + downlight).

        Rules:
        - Width <= 4m: 1 row (1 linear + 2 downlights per segment)
        - Every +3m width: +1 row

        Args:
            length: Corridor length in meters
            width: Corridor width in meters

        Returns:
            dict with counts and positions
        """
        # Calculate number of rows based on width
        num_rows = 1 + int((width - self.min_corridor_width) /
                           self.width_increment)
        num_rows = max(1, num_rows)

        # Calculate segments (each segment = 1 linear + 2 downlights)
        num_segments = math.ceil(length / self.fixture_spacing)

        # Total fixtures
        total_linear = num_rows * num_segments
        total_downlights = num_rows * num_segments * 2

        # Generate positions
        positions = []
        row_spacing = width / (num_rows + 1)

        for row in range(num_rows):
            y_pos = row_spacing * (row + 1)
            for i in range(num_segments):
                x_base = i * self.fixture_spacing

                # Linear fixture (center)
                positions.append({
                    "x": x_base,
                    "y": y_pos,
                    "type": "linear",
                    "series": "恒",
                    "power": 18,
                    "row": row + 1
                })

                # Downlight 1 (before linear)
                positions.append({
                    "x": x_base - 1.0,
                    "y": y_pos,
                    "type": "downlight",
                    "series": "佳",
                    "power": 8,
                    "row": row + 1
                })

                # Downlight 2 (after linear)
                positions.append({
                    "x": x_base + 1.0,
                    "y": y_pos,
                    "type": "downlight",
                    "series": "佳",
                    "power": 8,
                    "row": row + 1
                })

        return {
            "scheme": "scheme2",
            "corridor_length": length,
            "corridor_width": width,
            "num_rows": num_rows,
            "num_segments": num_segments,
            "linear_count": total_linear,
            "downlight_count": total_downlights,
            "positions": positions,
            "summary": (
                f"方案2: {num_rows}排灯具，"
                f"共{total_linear}个恒18W线形灯 + "
                f"{total_downlights}个佳8W筒灯"
            )
        }

    def calculate_service_center_layout(
        self,
        length: float,
        width: float
    ) -> Dict:
        """Calculate SDL layout for service center.

        Creates a rectangular ring with:
        - Dimensions: (length - 0.5m) × (width - 0.5m)
        - Suspended 1.4m from ceiling
        - Upper light: SDL module (1800-12000K)
        - Lower light: LED strip (4000K)
        - Film width: 0.15m

        Args:
            length: Service center length in meters
            width: Service center width in meters

        Returns:
            dict with SDL layout details
        """
        # Adjust dimensions (subtract 0.5m from each side)
        ring_length = length - 0.5
        ring_width = width - 0.5

        # Calculate perimeter
        perimeter = 2 * (ring_length + ring_width)

        # Film specifications
        film_width = 0.15  # meters
        suspension_height = 1.4  # meters

        # Estimate module count (assume 1.5m per module)
        module_length = 1.5
        num_modules = math.ceil(perimeter / module_length)

        # LED strip (5m per roll, 60W per roll)
        strip_length_per_roll = 5.0
        num_strips = math.ceil(perimeter / strip_length_per_roll)

        return {
            "scheme": "sdl",
            "service_center_length": length,
            "service_center_width": width,
            "ring_length": ring_length,
            "ring_width": ring_width,
            "perimeter": perimeter,
            "film_width": film_width,
            "suspension_height": suspension_height,
            "module_count": num_modules,
            "led_strip_rolls": num_strips,
            "total_strip_length": perimeter,
            "positions": [
                {
                    "type": "ring",
                    "x": 0.25,
                    "y": 0.25,
                    "length": ring_length,
                    "width": ring_width,
                    "upper_light": "天幕SDL模组",
                    "lower_light": "光跃Ray低压灯带"
                }
            ],
            "summary": (
                f"SDL方案: {ring_length:.1f}m × {ring_width:.1f}m 环形灯，"
                f"需要{num_modules}个SDL模组 + {num_strips}卷LED灯带"
            )
        }

    def calculate_station_hall_layout(
        self,
        outer_corridor_count: int,
        outer_corridor_width: float,
        inner_corridor_length: float,
        inner_corridor_width: float,
        service_center_length: float,
        service_center_width: float,
        scheme: str = "scheme1"
    ) -> Dict:
        """Calculate complete station hall layout.

        Args:
            outer_corridor_count: Number of outer corridors (1 or 2)
            outer_corridor_width: Width of outer corridors (m)
            inner_corridor_length: Length of inner corridor (m)
            inner_corridor_width: Width of inner corridor (m)
            service_center_length: Service center length (m)
            service_center_width: Service center width (m)
            scheme: Design scheme for corridors

        Returns:
            dict with complete station layout
        """
        results = {
            "scheme": scheme,
            "areas": {},
            "total_linear": 0,
            "total_downlight": 0,
            "total_modules": 0,
            "total_led_strips": 0
        }

        # Outer corridors (assume 20m length each)
        outer_corridor_length = 20.0
        for i in range(outer_corridor_count):
            area_name = f"外通道{i+1}"
            layout = self.calculate_corridor_layout(
                outer_corridor_length,
                outer_corridor_width,
                scheme
            )
            results["areas"][area_name] = layout
            results["total_linear"] += layout["linear_count"]
            results["total_downlight"] += layout["downlight_count"]

        # Inner corridor
        inner_layout = self.calculate_corridor_layout(
            inner_corridor_length,
            inner_corridor_width,
            scheme
        )
        results["areas"]["站厅内通道"] = inner_layout
        results["total_linear"] += inner_layout["linear_count"]
        results["total_downlight"] += inner_layout["downlight_count"]

        # Service center (SDL scheme)
        sdl_layout = self.calculate_service_center_layout(
            service_center_length,
            service_center_width
        )
        results["areas"]["客服中心"] = sdl_layout
        results["total_modules"] = sdl_layout["module_count"]
        results["total_led_strips"] = sdl_layout["led_strip_rolls"]

        # Summary
        results["summary"] = {
            "总计": (
                f"线形灯: {results['total_linear']}个, "
                f"筒灯: {results['total_downlight']}个, "
                f"SDL模组: {results['total_modules']}个, "
                f"LED灯带: {results['total_led_strips']}卷"
            )
        }

        return results


# Global instance
layout_calculator = MetroLayoutCalculator()
