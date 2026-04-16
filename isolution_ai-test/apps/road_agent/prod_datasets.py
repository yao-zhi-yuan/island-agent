import pandas as pd


class ProdDataset:
    def __init__(self):
        self.prod_file = "data/道路行业产品库.csv"
        self.prod_df = self.load_prod_data()
        df = self.prod_df
        self.pole_series_ls = df[
            df["二级分类名称"] == "灯杆"
        ]["系列"].unique().tolist()
        self.light_series_ls = df[
            df["二级分类名称"] == "路灯"
        ]["系列"].unique().tolist()
        self.module_series_ls = df[
            df["二级分类名称"] == "模组"
        ]["系列"].unique().tolist()

        # metro-specific lists: extract from metro industry products
        metro_df = df[df["行业"].str.contains("轨交", na=False)]
        
        # Metro linear fixtures (线形灯具)
        self.metro_linear_series_ls = metro_df[
            metro_df["一级分类名称"] == "线形灯具"
        ]["系列"].unique().tolist()
        
        # Metro recessed fixtures (筒灯)
        self.metro_recessed_series_ls = metro_df[
            metro_df["一级分类名称"] == "筒灯"
        ]["系列"].unique().tolist()
        
        # Metro modules (模组)
        self.metro_module_series_ls = metro_df[
            metro_df["一级分类名称"] == "模组"
        ]["系列"].unique().tolist()
        
        # Metro LED strips (低压灯带)
        self.metro_led_strip_series_ls = metro_df[
            metro_df["一级分类名称"] == "低压灯带"
        ]["系列"].unique().tolist()
        
        # All metro fixture series combined
        self.metro_fixture_series_ls = list(set(
            self.metro_linear_series_ls +
            self.metro_recessed_series_ls +
            self.metro_module_series_ls +
            self.metro_led_strip_series_ls
        ))

    def load_prod_data(self):
        df = pd.read_csv(self.prod_file, encoding="utf-8")
        df = df.fillna("")
        df = df[df["status"] == 1]

        return df


prod_dataset = ProdDataset()
