"""Metro BOM (Bill of Materials) generator.

This module generates detailed BOM lists with cost estimates
for metro lighting projects.
"""

from typing import Dict
from apps.metro_agent.prod_selector import metro_selector


class MetroBOMGenerator:
    """Generate BOM for metro lighting projects."""

    def __init__(self):
        self.selector = metro_selector

    def generate_bom(self, layout_result: Dict) -> Dict:
        """Generate BOM from layout calculation result.

        Args:
            layout_result: Output from MetroLayoutCalculator

        Returns:
            dict with BOM details including items, quantities, prices
        """
        bom = {
            "project_info": {
                "scheme": layout_result.get("scheme", "unknown"),
                "areas": list(layout_result.get("areas", {}).keys())
            },
            "items": [],
            "summary": {
                "total_items": 0,
                "total_cost": 0.0,
                "total_power": 0.0
            }
        }

        # Process each area
        for area_name, area_layout in layout_result.get("areas", {}).items():
            scheme = area_layout.get("scheme", "")

            if scheme in ["scheme1", "scheme2"]:
                # Corridor lighting
                self._add_corridor_items(bom, area_name, area_layout)
            elif scheme == "sdl":
                # Service center SDL lighting
                self._add_sdl_items(bom, area_name, area_layout)

        # Calculate totals
        bom["summary"]["total_items"] = len(bom["items"])
        bom["summary"]["total_cost"] = sum(
            item.get("subtotal", 0) for item in bom["items"]
        )
        bom["summary"]["total_power"] = sum(
            item.get("total_power", 0) for item in bom["items"]
        )

        return bom

    def _add_corridor_items(
        self,
        bom: Dict,
        area_name: str,
        layout: Dict
    ):
        """Add corridor lighting items to BOM.

        Args:
            bom: BOM dict to update
            area_name: Name of the area
            layout: Layout calculation result
        """
        scheme = layout.get("scheme", "")

        # Linear fixtures
        linear_count = layout.get("linear_count", 0)
        if linear_count > 0:
            if scheme == "scheme1":
                # 朗型 40W
                linear_products = self.selector.select_linear_fixture(
                    series="朗型",
                    power=40,
                    color_temp=4000
                )
            else:  # scheme2
                # 恒 18W
                linear_products = self.selector.select_linear_fixture(
                    series="恒",
                    power=18,
                    color_temp=4000
                )

            if len(linear_products) > 0:
                prod = linear_products.iloc[0]
                unit_price = prod.get("产品价格", 0)
                if unit_price == "":
                    unit_price = 0
                unit_price = float(unit_price)

                bom["items"].append({
                    "area": area_name,
                    "category": "线形灯具",
                    "material_no": prod.get("物料号", ""),
                    "description": prod.get("物料描述", ""),
                    "series": prod.get("系列", ""),
                    "power": prod.get("功率(w)", 0),
                    "color_temp": prod.get("色温(k)", ""),
                    "quantity": linear_count,
                    "unit": "套",
                    "unit_price": unit_price,
                    "subtotal": unit_price * linear_count,
                    "total_power": prod.get("功率(w)", 0) * linear_count,
                    "luminous_flux": prod.get("光通量(lm)", 0),
                    "efficacy": prod.get("光效(lm/w)", 0)
                })

        # Downlights (only for scheme2)
        downlight_count = layout.get("downlight_count", 0)
        if downlight_count > 0:
            downlight_products = self.selector.select_recessed_downlight(
                series="佳",
                power=8,
                color_temp=4000
            )

            if len(downlight_products) > 0:
                prod = downlight_products.iloc[0]
                unit_price = prod.get("产品价格", 0)
                if unit_price == "":
                    unit_price = 0
                unit_price = float(unit_price)

                bom["items"].append({
                    "area": area_name,
                    "category": "筒灯",
                    "material_no": prod.get("物料号", ""),
                    "description": prod.get("物料描述", ""),
                    "series": prod.get("系列", ""),
                    "power": prod.get("功率(w)", 0),
                    "color_temp": prod.get("色温(k)", ""),
                    "quantity": downlight_count,
                    "unit": "套",
                    "unit_price": unit_price,
                    "subtotal": unit_price * downlight_count,
                    "total_power": prod.get("功率(w)", 0) * downlight_count,
                    "luminous_flux": prod.get("光通量(lm)", 0),
                    "efficacy": prod.get("光效(lm/w)", 0)
                })

    def _add_sdl_items(
        self,
        bom: Dict,
        area_name: str,
        layout: Dict
    ):
        """Add SDL lighting items to BOM.

        Args:
            bom: BOM dict to update
            area_name: Name of the area
            layout: Layout calculation result
        """
        # SDL modules
        module_count = layout.get("module_count", 0)
        if module_count > 0:
            module_products = self.selector.select_module(
                series="天幕",
                color_temp_range="1800-12000"
            )

            if len(module_products) > 0:
                prod = module_products.iloc[0]
                unit_price = prod.get("产品价格", 0)
                if unit_price == "":
                    unit_price = 0
                unit_price = float(unit_price)

                bom["items"].append({
                    "area": area_name,
                    "category": "SDL模组",
                    "material_no": prod.get("物料号", ""),
                    "description": prod.get("物料描述", ""),
                    "series": prod.get("系列", ""),
                    "power": prod.get("功率(w)", 0),
                    "color_temp": prod.get("色温(k)", ""),
                    "quantity": module_count,
                    "unit": "套",
                    "unit_price": unit_price,
                    "subtotal": unit_price * module_count,
                    "total_power": prod.get("功率(w)", 0) * module_count,
                    "luminous_flux": prod.get("光通量(lm)", ""),
                    "efficacy": prod.get("光效(lm/w)", 0)
                })

        # LED strips
        strip_count = layout.get("led_strip_rolls", 0)
        if strip_count > 0:
            strip_products = self.selector.select_led_strip(
                series="光跃 Ray",
                color_temp_range="1800-12000"
            )

            if len(strip_products) > 0:
                prod = strip_products.iloc[0]
                unit_price = prod.get("产品价格", 0)
                if unit_price == "":
                    unit_price = 0
                unit_price = float(unit_price)

                bom["items"].append({
                    "area": area_name,
                    "category": "LED灯带",
                    "material_no": prod.get("物料号", ""),
                    "description": prod.get("物料描述", ""),
                    "series": prod.get("系列", ""),
                    "power": prod.get("功率(w)", 0),
                    "color_temp": prod.get("色温(k)", ""),
                    "quantity": strip_count,
                    "unit": "卷",
                    "unit_price": unit_price,
                    "subtotal": unit_price * strip_count,
                    "total_power": prod.get("功率(w)", 0) * strip_count,
                    "luminous_flux": prod.get("光通量(lm)", ""),
                    "efficacy": prod.get("光效(lm/w)", 0)
                })

    def format_bom_table(self, bom: Dict) -> str:
        """Format BOM as a text table.

        Args:
            bom: BOM dict from generate_bom

        Returns:
            str: Formatted table
        """
        lines = []
        lines.append("=" * 120)
        lines.append("物料清单 (BOM)")
        lines.append("=" * 120)

        # Header
        header = (
            f"{'区域':<12} {'类别':<10} {'物料号':<15} "
            f"{'描述':<30} {'数量':<8} {'单价':<10} {'小计':<10}"
        )
        lines.append(header)
        lines.append("-" * 120)

        # Items
        for item in bom["items"]:
            row = (
                f"{item['area']:<12} "
                f"{item['category']:<10} "
                f"{item['material_no']:<15} "
                f"{item['description']:<30} "
                f"{item['quantity']:<8} "
                f"¥{item['unit_price']:<9.2f} "
                f"¥{item['subtotal']:<9.2f}"
            )
            lines.append(row)

        # Summary
        lines.append("-" * 120)
        summary = bom["summary"]
        lines.append(
            f"合计: {summary['total_items']}项  "
            f"总功率: {summary['total_power']:.1f}W  "
            f"总价: ¥{summary['total_cost']:.2f}"
        )
        lines.append("=" * 120)

        return "\n".join(lines)


# Global instance
bom_generator = MetroBOMGenerator()
