cd "$1" && python3 - <<'PY'
# 惜しい誤答: by_store を少ない順に並べる
import pandas as pd, openpyxl
from openpyxl.chart import LineChart, Reference
df = pd.read_csv("sales.csv"); df["month"] = df["date"].str[:7]
s = df.groupby("store")["amount"].sum().sort_values(ascending=True).reset_index().rename(columns={"amount": "total"})
m = df.groupby("month")["amount"].sum().sort_index().reset_index().rename(columns={"amount": "total"})
with pd.ExcelWriter("report.xlsx", engine="openpyxl") as x:
    s.to_excel(x, sheet_name="by_store", index=False); m.to_excel(x, sheet_name="by_month", index=False)
wb = openpyxl.load_workbook("report.xlsx"); ws = wb["by_month"]
ch = LineChart(); ch.add_data(Reference(ws, min_col=2, min_row=1, max_row=ws.max_row), titles_from_data=True); ch.set_categories(Reference(ws, min_col=1, min_row=2, max_row=ws.max_row))
ws.add_chart(ch, "D2"); wb.save("report.xlsx")
PY
