"""経費精算の一次判定コーパス v2（レビュー指摘を反映）

v1 の欠陥: 言い回しと正解が1対1で、金額を読まない分類器が91.7%を出した。
v2 の方針:
  1. 金額が判定を決める項目を意図して増やす。
     「業務・領収書あり・部長承認なし」は金額が5万円未満なら承認、以上なら保留。
     ここを A/B で均衡させ、「承認なし→保留」の近道を半分外れにする。
  2. 各属性の言い回しを複数用意し、学習とテストで別の言い回しを使う(分布外テスト)。
  3. 曖昧な言い回し(二重否定・「証憑」・「了承」)を廃止する。
  4. 規程2「要確認」の理由(用途不明/金額不明/領収書なし)を均等にする。
  5. 金額の書き方(そのまま/単価×人数/万円表記/内訳の合計)で計算の難しさを作る。
正解は規程から機械的に決まる(判定者の主観を入れない)。
"""
import json, random, hashlib
from collections import Counter

THRESH = 50000

def policy_text(th=THRESH):
    return ("【経費精算規程】次の順に当てはめ、最初に該当したものを判定とする。\n"
            "1. 私的用途(業務と無関係な支出)は「却下」\n"
            "2. 金額または用途が特定できないものは「要確認」\n"
            "3. 領収書がないものは「要確認」\n"
            "4. 金額が%s円以上で、部長の承認がないものは「保留」\n"
            "5. 上記のいずれにも当たらないものは「承認」" % format(th, ","))

LABEL_JA = {"A":"承認","B":"保留","C":"却下","D":"要確認"}

def truth(a, th=THRESH):
    if a["kind"] == "private": return "C"
    if a["amount"] is None or a["kind"] == "unknown": return "D"
    if not a["receipt"]: return "D"
    if a["amount"] >= th and not a["mgr"]: return "B"
    return "A"

# ---- 言い回しプール。各プールを学習用とテスト用に二分する ----
P = {
 "biz": ["取引先との会食","出張の新幹線代","業務用の技術書","顧客向けデモ機材のレンタル",
         "社外セミナーの参加費","業務用ソフトウェアのライセンス","展示会の出展料","客先訪問のタクシー代",
         "採用イベントの会場費","社内研修の講師謝礼"],
 "private": ["家族との夕食","私用の衣類","個人の旅行","自宅用の家電","趣味のゴルフ用品","子どもの習い事"],
 "unk_purpose": ["例の件","先日の案件","前回の分","いつものもの"],
 "rc_yes": ["領収書を添付しました。","領収書は提出済みです。","レシートを添付しています。",
            "領収書の原本があります。","領収書のPDFを添付しました。","領収書は経理に回しました。"],
 "rc_no":  ["領収書はもらい忘れました。","領収書を紛失しました。","領収書は発行されませんでした。",
            "レシートは捨ててしまいました。","領収書はありません。","領収書を受け取っていません。"],
 "mg_yes": ["部長の承認を得ています。","部長決裁済みです。","部長から承認をもらいました。",
            "部長の決裁が下りています。","部長承認済みです。","部長に承認されています。"],
 "mg_no":  ["部長の承認はまだです。","部長決裁は未取得です。","部長にはまだ申請していません。",
            "部長の承認は取れていません。","部長決裁はこれからです。","部長の承認を待っています。"],
 "amt_unk":["金額は後で確認します。","金額はまだ分かりません。","金額は請求書が届いてから連絡します。",
            "金額は未確定です。"],
}

def split_pools(rnd):
    tr, te = {}, {}
    for k, v in P.items():
        v = v[:]; rnd.shuffle(v); h = max(1, len(v)//2)
        tr[k], te[k] = v[:h], v[h:]
    return tr, te

def yen(n): return format(n, ",") + "円"

def amount_phrase(amt, style, rnd):
    """金額の書き方で計算の難しさを作る。indirect は必ず計算が要る形にする。"""
    if style != "indirect":
        return "金額は%sです。" % yen(amt)
    forms = []
    for k in (2,3,4,5,6,8,10,12):
        if amt % k == 0: forms.append(("unit", k))
    if amt % 10000 == 0 or amt % 1000 == 0: forms.append(("man", None))
    forms.append(("parts", None))
    kind, k = rnd.choice(forms)
    if kind == "unit":  return "1人あたり%sで、%d人分です。" % (yen(amt//k), k)
    if kind == "man":   return "金額は%s万円です。" % (("%.1f" % (amt/10000)).rstrip("0").rstrip("."))
    a1 = rnd.randrange(1000, amt-1000, 1000) if amt > 3000 else amt//2
    return "内訳は本体%sと税・手数料%sです。" % (yen(a1), yen(amt-a1))

def render(a, style, pool, rnd):
    pur = a["purpose"]
    if style == "explicit":
        lines = ["用途: " + (pur if a["kind"]!="unknown" else rnd.choice(pool["unk_purpose"])),
                 "金額: " + (yen(a["amount"]) if a["amount"] is not None else "未定"),
                 "領収書: " + rnd.choice(pool["rc_yes"] if a["receipt"] else pool["rc_no"]).rstrip("。"),
                 "部長承認: " + rnd.choice(pool["mg_yes"] if a["mgr"] else pool["mg_no"]).rstrip("。")]
        return "\n".join(lines)
    head = ("%sの精算です。" % pur) if a["kind"]!="unknown" else ("%sの精算です。" % rnd.choice(pool["unk_purpose"]))
    amt = rnd.choice(pool["amt_unk"]) if a["amount"] is None else amount_phrase(a["amount"], style, rnd)
    rc = rnd.choice(pool["rc_yes"] if a["receipt"] else pool["rc_no"])
    mg = rnd.choice(pool["mg_yes"] if a["mgr"] else pool["mg_no"])
    parts = [head, amt, rc, mg]
    if style == "narrative": rnd.shuffle(parts[1:])
    return "".join(parts)

SMALL = [3000, 8000, 12000, 18000, 24000, 30000, 36000, 42000, 45000, 48000, 49000]
LARGE = [50000, 51000, 54000, 60000, 72000, 80000, 96000, 120000, 150000]
MID   = [30000, 32000, 36000, 40000, 42000, 45000, 48000]   # 規程変更(3万)で A→B に反転する帯

def make_items(n, pool, rnd):
    """正解を均等に、かつ A/B の中で金額が決め手になる項目を厚くする。"""
    items = []
    per = n // 4
    for _ in range(per):  # B: 業務・領収書あり・承認なし・5万以上
        items.append(dict(kind="biz", purpose=rnd.choice(pool["biz"]), amount=rnd.choice(LARGE), receipt=True, mgr=False))
    for i in range(per):  # A: 85%を「承認なし・5万未満」にして、金額を読まないと B と区別できなくする
        if i % 20 < 17:
            amt = rnd.choice(MID) if i % 2 == 0 else rnd.choice([a for a in SMALL if a < 30000])
            items.append(dict(kind="biz", purpose=rnd.choice(pool["biz"]), amount=amt, receipt=True, mgr=False))
        else:
            items.append(dict(kind="biz", purpose=rnd.choice(pool["biz"]), amount=rnd.choice(SMALL+LARGE), receipt=True, mgr=True))
    for _ in range(per):  # C: 私的用途(他の属性はランダム)
        items.append(dict(kind="private", purpose=rnd.choice(pool["private"]),
                          amount=rnd.choice(SMALL+LARGE+[None]), receipt=rnd.random()<.5, mgr=rnd.random()<.5))
    for i in range(per):  # D: 理由を3等分
        r = i % 3
        if r == 0: items.append(dict(kind="unknown", purpose=None, amount=rnd.choice(SMALL+LARGE), receipt=True, mgr=rnd.random()<.5))
        if r == 1: items.append(dict(kind="biz", purpose=rnd.choice(pool["biz"]), amount=None, receipt=True, mgr=rnd.random()<.5))
        if r == 2: items.append(dict(kind="biz", purpose=rnd.choice(pool["biz"]), amount=rnd.choice(SMALL+LARGE), receipt=False, mgr=rnd.random()<.5))
    return items

def reason(a):
    if a["kind"]=="private": return "private"
    if a["kind"]=="unknown": return "purpose_unknown"
    if a["amount"] is None: return "amount_unknown"
    if not a["receipt"]: return "no_receipt"
    if a["mgr"]: return "approved"
    return "amount_decides"

def build(seed=20260923, n_train=200, n_test=400):
    rnd = random.Random(seed)
    pool_tr, pool_te = split_pools(rnd)
    rows = []
    for split, n, pool in (("train", n_train, pool_tr), ("test", n_test, pool_te)):
        base = make_items(n, pool, rnd)
        styles = (["explicit","narrative","indirect"] * (len(base)//3 + 1))[:len(base)]
        rnd.shuffle(styles)
        for a, st in zip(base, styles):
            if a["amount"] is None and st == "indirect": st = "narrative"
            text = render(a, st, pool, rnd)
            y = truth(a); y30 = truth(a, 30000)
            rows.append(dict(id=hashlib.sha1((split+st+text).encode()).hexdigest()[:10],
                             split=split, style=st, text=text, label=y, label_th30=y30,
                             reason=reason(a), amount=a["amount"], kind=a["kind"],
                             receipt=a["receipt"], mgr=a["mgr"],
                             boundary=int(a["amount"] in (49000,50000,51000)) if a["amount"] else 0))
    return rows, pool_tr, pool_te

if __name__ == "__main__":
    rows, ptr, pte = build()
    json.dump(dict(policy=policy_text(), policy_th30=policy_text(30000), labels=LABEL_JA,
                   phrase_split=dict(train=ptr, test=pte), rows=rows),
              open("data/corpus.json","w"), ensure_ascii=False, indent=1)
    te=[r for r in rows if r["split"]=="test"]; tr=[r for r in rows if r["split"]=="train"]
    print("学習 %d / テスト %d" % (len(tr), len(te)))
    print("テスト正解", dict(Counter(r["label"] for r in te)))
    print("テスト理由", dict(Counter(r["reason"] for r in te)))
    print("テスト文体", dict(Counter(r["style"] for r in te)))
    print("規程変更(3万)で正解が変わる項目:", sum(r["label"]!=r["label_th30"] for r in te))
    # 言い回しの重なりがないこと
    ov = {k: set(ptr[k]) & set(pte[k]) for k in ptr}
    print("学習とテストで共有する言い回し:", {k:len(v) for k,v in ov.items() if v} or "なし")
    # ---- 近道の下限: 金額を一切読まずに (用途区分, 領収書, 承認) だけで当てる ----
    key=lambda r:(r["kind"], r["amount"] is None, r["receipt"], r["mgr"])
    tab={}
    for r in tr: tab.setdefault(key(r),Counter())[r["label"]]+=1
    def shortcut(r):
        c=tab.get(key(r))
        return c.most_common(1)[0][0] if c else "D"
    acc=sum(shortcut(r)==r["label"] for r in te)/len(te)
    print("近道(金額を読まない)の正答率: %.1f%%  ← 全方式が超えるべき下限" % (100*acc))
    by=Counter(); tot=Counter()
    for r in te: tot[r["style"]]+=1; by[r["style"]]+= shortcut(r)==r["label"]
    print("   文体別:", {k:"%.1f%%" % (100*by[k]/tot[k]) for k in tot})
    json.dump({"shortcut_acc":acc}, open("data/shortcut.json","w"))
    for st in ("explicit","narrative","indirect"):
        for r in [x for x in te if x["style"]==st and x["reason"]=="amount_decides"][:2]:
            print("  [%s/%s] %s" % (st, r["label"], r["text"].replace("\n"," / ")))
