import csv, os, random, sys
def gen():
    rnd = random.Random(1101); rows = []
    for i in range(1500):
        m = rnd.randint(1, 12); d = rnd.randint(1, 28)
        rows.append(["2025-%02d-%02d" % (m, d), rnd.choice(["渋谷", "梅田", "天神", "札幌", "名古屋"]), rnd.choice(["食品", "雑貨", "衣料"]), rnd.randint(300, 30000)])
    return rows
if __name__ == "__main__":
    w = csv.writer(open(os.path.join(sys.argv[1], "sales.csv"), "w", newline="", encoding="utf-8")); w.writerow(["date", "store", "category", "amount"]); w.writerows(gen())
