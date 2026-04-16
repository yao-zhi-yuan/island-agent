"""Metro product selection module.

This module provides functions to select appropriate lighting products
for metro/subway projects based on requirements like:
- Area type (customer service center, station hall corridor)
- Design scheme (linear + downlight, linear only, SDL module)
- Technical specifications (power, color temperature, dimensions)
"""

from apps.road_agent.prod_datasets import prod_dataset


class MetroProductSelector:
    """Select metro lighting products from the database."""

    def __init__(self):
        self.df = prod_dataset.prod_df
        # Filter for metro products only
        self.metro_df = self.df[
            self.df["行业"].str.contains("轨交", na=False)
        ]
    
    def select_control_room_product(self, series=None, color_temp=None, size=None):
        """Select control room lighting product.

        Args:
            series: Series name (e.g., "佳IV", "天境")
            color_temp: Color temperature in K (e.g., 4000, "1800-12000")
            size: Size string (e.g., "600*600")

        Returns:
            pandas DataFrame with matching products
        """
        result = self.metro_df[
            self.metro_df["一级分类名称"] == "灯盘"
        ].copy()

        if series:
            result = result[result["系列"] == series]
        if color_temp:
            # Allow for different separators in range ('-' or '~')
            color_temp_str = str(color_temp)
            if '-' in color_temp_str or '~' in color_temp_str:
                parts = color_temp_str.replace('~', '-').split('-')
                if len(parts) == 2:
                    # Regex to match range with either separator
                    regex = fr"{parts[0]}[-~]{parts[1]}"
                    result = result[
                        result["色温(k)"].astype(str).str.contains(
                            regex, na=False, regex=True
                        )
                    ]
            else:
                result = result[
                    result["色温(k)"].astype(str).str.contains(
                        color_temp_str, na=False
                    )
                ]
        if size:
            size_str = str(size)
            if '*' in size_str:
                try:
                    w, h = size_str.split('*')[:2]
                    # Create regex to match W*H or H*W, followed by anything
                    regex = fr"({w}\*{h}|{h}\*{w})"
                    result = result[
                        result["尺寸"].astype(str).str.contains(
                            regex, na=False, regex=True
                        )
                    ]
                except ValueError:
                    # Fallback for sizes that don't fit W*H format
                    result = result[
                        result["尺寸"].astype(str).str.contains(
                            size_str, na=False
                        )
                    ]
            else:
                result = result[
                    result["尺寸"].astype(str).str.contains(
                        size_str, na=False
                    )
                ]
        return result

    def select_linear_fixture(self, series=None, power=None,
                              color_temp=None, installation=None):
        """Select linear fixture (线形灯具).

        Args:
            series: Series name (e.g., "朗型", "恒")
            power: Power in watts (e.g., 40)
            color_temp: Color temperature in K (e.g., 4000)
            installation: Installation method (e.g., "嵌装", "吊线")

        Returns:
            pandas DataFrame with matching products
        """
        result = self.metro_df[
            self.metro_df["一级分类名称"] == "线形灯具"
        ].copy()

        if series:
            result = result[result["系列"] == series]
        if power:
            result = result[result["功率(w)"] == float(power)]
        if color_temp:
            # Color temp in CSV is string, need to convert for comparison
            result = result[
                result["色温(k)"].astype(str) == str(color_temp)
            ]
        if installation:
            if installation == "嵌装":
                result = result[
                    result["二级分类名称"].str.contains("嵌入式", na=False)
                ]
            elif installation == "吊线":
                result = result[
                    result["二级分类名称"].str.contains("吊线式", na=False)
                ]

        return result

    def select_recessed_downlight(self, series=None, power=None,
                                  color_temp=None, opening=None):
        """Select recessed downlight (筒灯).

        Args:
            series: Series name (e.g., "佳")
            power: Power in watts (e.g., 8)
            color_temp: Color temperature in K (e.g., 4000)
            opening: Opening diameter in mm (e.g., 125)

        Returns:
            pandas DataFrame with matching products
        """
        result = self.metro_df[
            self.metro_df["一级分类名称"] == "筒灯"
        ].copy()

        if series:
            result = result[result["系列"] == series]
        if power:
            result = result[result["功率(w)"] == float(power)]
        if color_temp:
            result = result[result["色温(k)"].astype(str) == str(color_temp)]
        if opening:
            result = result[result["开孔"] == str(opening)]

        return result

    def select_module(self, series=None, color_temp_range=None):
        """Select lighting module (模组).

        Args:
            series: Series name (e.g., "天幕")
            color_temp_range: Color temp range string (e.g., "1800-12000")

        Returns:
            pandas DataFrame with matching products
        """
        result = self.metro_df[
            self.metro_df["一级分类名称"] == "模组"
        ].copy()

        if series:
            result = result[result["系列"] == series]
        if color_temp_range:
            result = result[
                result["色温(k)"].astype(str).str.contains(
                    color_temp_range, na=False
                )
            ]

        return result

    def select_led_strip(self, series=None, color_temp_range=None):
        """Select LED strip (低压灯带).

        Args:
            series: Series name (e.g., "光跃 Ray")
            color_temp_range: Color temp range string (e.g., "1800-12000")

        Returns:
            pandas DataFrame with matching products
        """
        result = self.metro_df[
            self.metro_df["一级分类名称"] == "低压灯带"
        ].copy()

        if series:
            result = result[result["系列"] == series]
        if color_temp_range:
            result = result[
                result["色温(k)"].astype(str).str.contains(
                    color_temp_range, na=False
                )
            ]

        return result

    def get_scheme_1_products(self):
        """Get products for Scheme 1: Linear + Downlight.

        Requirements:
        - Linear: 恒, 18W, 4000K, 1.2m, recessed
        - Downlight: 佳, 8W, 4000K, 125mm opening, recessed/surface

        Returns:
            dict with 'linear' and 'downlight' DataFrames
        """
        linear = self.select_linear_fixture(
            series="恒", power=18, color_temp=4000, installation="吊线"
        )

        downlight = self.select_recessed_downlight(
            series="佳",
            power=8,
            color_temp=4000,
            opening=125
        )

        return {
            "linear": linear,
            "downlight": downlight,
            "scheme_name": "线条灯+筒灯方案"
        }

    def get_scheme_2_products(self):
        """Get products for Scheme 2: Linear fixtures only.

        Requirements:
        - Linear: 恒, 18W, 4000K, 1.2m, pendant
        - Downlight: 佳, 8W, 4000K, 125mm (same as scheme 1)

        Returns:
            dict with 'linear' and 'downlight' DataFrames
        """
        linear = self.select_linear_fixture(
            series="恒",
            power=18,
            color_temp=4000,
            installation="吊线"
        )

        downlight = self.select_recessed_downlight(
            series="佳",
            power=8,
            color_temp=4000,
            opening=125
        )

        return {
            "linear": linear,
            "downlight": downlight,
            "scheme_name": "高效光"
        }

    def get_sdl_scheme_products(self):
        """Get products for SDL Scheme: Customer service center.

        Requirements:
        - Module: 天幕, tunable white (1800-12000K), SDL
        - LED Strip: 光跃 Ray, 4000K (lower light), tunable (upper)

        Returns:
            dict with 'module' and 'led_strip' DataFrames
        """
        module = self.select_module(
            series="天幕",
            color_temp_range="1800-12000"
        )

        led_strip = self.select_led_strip(
            series="光跃 Ray",
            color_temp_range="1800-12000"
        )

        return {
            "module": module,
            "led_strip": led_strip,
            "scheme_name": "SDL方案-客服中心"
        }

    def get_available_options(self, category):
        """Get available options for a product category.

        Args:
            category: "线形灯具", "筒灯", "模组", or "低压灯带"

        Returns:
            dict with available series, powers, color_temps
        """
        cat_df = self.metro_df[
            self.metro_df["一级分类名称"] == category
        ]

        series_list = cat_df["系列"].dropna().unique().tolist()
        power_list = sorted(
            cat_df["功率(w)"].dropna().unique().tolist()
        )
        ct_list = cat_df["色温(k)"].dropna().unique().tolist()

        return {
            "category": category,
            "series": series_list,
            "powers": power_list,
            "color_temps": ct_list,
            "count": len(cat_df)
        }

    def format_product_summary(self, products_df):
        """Format product DataFrame as human-readable summary.

        Args:
            products_df: pandas DataFrame with product info

        Returns:
            list of dict with formatted product info
        """
        if len(products_df) == 0:
            return []

        summary = []
        for _, row in products_df.iterrows():
            prod = {
                "物料号": row.get("物料号", ""),
                "物料描述": row.get("物料描述", ""),
                "系列": row.get("系列", ""),
                "功率": f"{row.get('功率(w)', '')}W",
                "色温": f"{row.get('色温(k)', '')}K",
                "光通量": f"{row.get('光通量(lm)', '')}lm",
                "光效": f"{row.get('光效(lm/w)', '')}lm/W",
                "显色指数": f"Ra{row.get('显色指数(ra)', '')}",
                "安装方式": row.get("安装方式", ""),
                "尺寸": row.get("尺寸", ""),
                "价格": f"¥{row.get('产品价格', '')}",
            }
            summary.append(prod)

        return summary


# Global instance
metro_selector = MetroProductSelector()
