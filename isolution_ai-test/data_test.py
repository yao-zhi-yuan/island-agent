import pandas as pd

excel_file = "data/道路行业产品库.csv"

df = pd.read_csv(excel_file, encoding="utf-8")
# convert to excel
df.to_csv("data/道路行业产品_utf8.csv", index=False, encoding="GBK")
df = df.fillna("")
df = df[df["行业"].str.contains("轨交", na=False)]
metro_light_series_ls = df["系列"].unique().tolist()
print("Metro Light Series List:")
for s in metro_light_series_ls:
    print(" -", s)