"""Extended Thinking は「考えながら喋る」のか。

反証可能な予測:
  普通のモデル → 難しい質問ほど喋り出し(TTFA)が遅くなる
  ET が本物なら → 難しくしても TTFA は伸びない(先に声を出すため)

条件はブロック内シャッフル(seed固定)。全試行を1行ずつ記録。
"""
import asyncio, os, sys, csv, random, time
from google.genai import types
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig
HERE = os.path.dirname(os.path.abspath(__file__))

SYS = "あなたは有能なアシスタントです。日本語で簡潔に答えてください。"

EASY = [("e1","日本の首都はどこですか。"),
        ("e2","1たす1はいくつですか。"),
        ("e3","水の化学式を教えてください。")]
HARD = [("h1","ある商品を原価の4割増しで定価にし、定価の2割引で売ったら利益が96円でした。原価はいくらですか。"),
        ("h2","A、B、Cの3人がいます。Aは嘘つきか正直者。『Bは嘘つきだ』とAが言い、『AとCは同じ種類だ』とBが言いました。Cは正直者です。Aは嘘つきですか。"),
        ("h3","時計の針が3時と4時の間で、長針と短針がちょうど重なるのは3時何分ですか。分数で答えてください。")]

MODELS = [("gemini-3.8-live-extended-thinking","HIGH"),
          ("gemini-3.8-live-extended-thinking","LOW"),
          ("gemini-3.8-live", None),
          ("gemini-3.1-flash-live-preview", None),
          ("gemini-2.5-flash-native-audio-latest", None)]

def cfg(level):
    c = types.LiveConnectConfig(
        response_modalities=["AUDIO"], system_instruction=SYS,
        output_audio_transcription=types.AudioTranscriptionConfig())
    if level: c.thinking_config = types.ThinkingConfig(thinking_level=level)
    return c

async def main():
    blocks = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20260918
    cells = [(m, lv, d, qid, q) for m, lv in MODELS
             for d, lst in (("easy", EASY), ("hard", HARD)) for qid, q in lst]
    rows = []
    rnd = random.Random(seed)
    print("条件%d x %dブロック = %d試行 / seed=%d / sdk=%s"
          % (len(cells), blocks, len(cells)*blocks, seed, rig.SDK))
    for b in range(blocks):
        order = cells[:]; rnd.shuffle(order)
        for i, (m, lv, diff, qid, q) in enumerate(order):
            wav = "%s/out/think/%s_%s_%s_b%d.wav" % (HERE, m.split("-live")[0][-3:] + (lv or "NA"), diff, qid, b)
            rec, tr = await rig.ask(m, cfg(lv), q, timeout=35.0, wav=wav)
            rec.update(level=lv or "", difficulty=diff, qid=qid,
                       block_index=b, trial_index=i, seed=seed)
            rows.append(rec)
            print("  b%d %-38s %-5s %-4s %s ttfa=%5s 完了%5s 無音%5s %r"
                  % (b, m, lv or "-", diff,
                     "ok " if rec["ok"] else ("ERR" if rec["err"] else "無音"),
                     rec.get("ttfa_ms"), rec.get("play_ms"), rec.get("max_silence_ms"),
                     (rec.get("first_say") or "")[:26]))
            await asyncio.sleep(0.5)
    fn = "%s/data/e16_thinking.csv" % HERE
    keys = sorted({k for r in rows for k in r})
    with open(fn, "w", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=keys); w.writeheader(); w.writerows(rows)
    print("saved:", fn, "rows:", len(rows))

if __name__ == "__main__":
    asyncio.run(main())
