# 別解: matplotlib で描いた PNG を貼る
cd "$1" && python3 - <<'PY'
import csv, collections, openpyxl, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from openpyxl.drawing.image import Image
st = collections.Counter(); mo = collections.Counter()
for r in csv.DictReader(open("sales.csv", encoding="utf-8")): st[r["store"]] += int(r["amount"]); mo[r["date"][:7]] += int(r["amount"])
wb = openpyxl.Workbook(); a = wb.active; a.title = "by_store"; a.append(["store", "total"])
for k, v in sorted(st.items(), key=lambda x: -x[1]): a.append([k, v])
b = wb.create_sheet("by_month"); b.append(["month", "total"])
for k in sorted(mo): b.append([k, mo[k]])
plt.plot(sorted(mo), [mo[k] for k in sorted(mo)]); plt.savefig("m.png"); b.add_image(Image("m.png"), "D2"); wb.save("report.xlsx")
PY
