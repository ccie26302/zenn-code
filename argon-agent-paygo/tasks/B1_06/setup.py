import csv, io, json, os, random, sys
def gen():
    rnd = random.Random(606); cust = []
    for i in range(1, 61):
        cust.append([i, "顧客%02d" % i, "" if i % 13 == 0 else "c%02d@example.com" % i])
    for i in (5, 17, 33):                                # 重複(後ろが正)
        cust.append([i, "顧客%02d(新)" % i, "new%02d@example.com" % i])
    rnd.shuffle(cust)
    orders = []
    for k in range(240):
        cid = rnd.choice(list(range(1, 56)) + [77, 88])     # 56-60 は注文なし、77/88 は顧客にない
        a = rnd.randint(100, 50000)
        amt = rnd.choice([a, str(a), "{:,}".format(a)])
        orders.append({"order_id": "O%04d" % k, "customer_id": cid, "amount": amt})
    s = io.StringIO(); w = csv.writer(s); w.writerow(["id", "name", "email"]); w.writerows(cust)
    return s.getvalue(), orders
if __name__ == "__main__":
    c, o = gen()
    open(os.path.join(sys.argv[1], "customers.csv"), "w", encoding="utf-8").write(c)
    json.dump(o, open(os.path.join(sys.argv[1], "orders.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
