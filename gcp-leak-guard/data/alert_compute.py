"""公開している2つの CSV(alert_audit_events.csv と alert_messages.csv)から、alerts.csv の秒数を出し直す。
起点 = 監査ログの timestamp(その回の操作の窓で最初の一致)、終点 = その回の試行用ポリシー "tN: <event>" の最初の通知の publishTime。
usage: python3 data/alert_compute.py   → alerts.csv と同じ形で標準出力"""
import csv, datetime, re

def ts(s):
    s = s.replace("Z", "+00:00")
    m = re.match(r"(.*\.\d{1,6})\d*(\+.*)", s)   # Python 3.9 はナノ秒を読めないのでマイクロ秒に切る
    return datetime.datetime.fromisoformat(m.group(1) + m.group(2) if m else s).timestamp()

audit = list(csv.DictReader(open("data/alert_audit_events.csv")))
msgs = list(csv.DictReader(open("data/alert_messages.csv")))
# 記事の1回目 = trial 1。鍵の作成は 03:07 の操作、残りの3つは作成15分後にやり直した 03:18:59〜 の操作(t1b)
PLAN = [
    (1, "t1_audit.json", "t1_msgs.jsonl", ["key_create"], "2026-10-09T03:07:00Z", "2026-10-09T03:08:00Z"),
    (1, "t1_audit.json", "t1b_msgs.jsonl", ["public_run", "public_gcs", "invoker_disabled"], "2026-10-09T03:18:50Z", "2026-10-09T03:20:00Z"),
    (2, "t2_audit.json", "t2_msgs.jsonl", ["key_create", "public_run", "public_gcs", "invoker_disabled"], "2026-10-09T03:37:00Z", "2026-10-09T03:38:00Z"),
    (4, "t4_audit.json", "t4_msgs.jsonl", ["key_create", "public_run", "public_gcs", "invoker_disabled"], "2026-10-09T04:07:50Z", "2026-10-09T04:08:30Z"),
]
print("trial,event,audit_ts,incident_started,publish_ts,latency_s,state")
for T, af, mf, events, start, end in PLAN:
    for k in events:
        a = min(ts(r["timestamp"]) for r in audit if r["file"] == af and r["event"] == k and ts(start) <= ts(r["timestamp"]) <= ts(end))
        m = sorted((r for r in msgs if r["file"] == mf and r["policy_name"] == f"t{T}: {k}"), key=lambda r: r["publishTime"])[0]
        p = ts(m["publishTime"])
        print(f"{T},{k},{a},{m['incident_started_at']},{p},{p - a:.1f},{m['state']}")
