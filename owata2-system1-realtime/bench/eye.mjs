// 目(画面の撮影＋ルールの判定)の応答時間ベンチマーク。ゲームは時計を止めたまま、毎回 1〜20 コマ進めて場面を変える(歩く・跳ぶを混ぜる)。
// 判断はしない(場面を変えるための操作は乱数で固定)。usage: node bench/eye.mjs [N=300]
import { Owata, ACTIONS2 } from "../harness/owata.mjs";
import fs from "node:fs";
const N = Number(process.argv[2] || 300), EYE = "http://127.0.0.1:8099";
let s = 7; const rnd = () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
const g = new Owata({}); await g.open(); await g.load();
if (!(await g.toGameplay()).ok) throw new Error("nav"); await g.resetAndFreeze();
await fetch(EYE + "/reset", { method: "POST" });
const acts = ["right", "right", "rightjump_big", "jump_big", "wait", "left"];
const rows = [];
for (let i = 0; i < N + 20; i++) {
  await g.actSpec(ACTIONS2[acts[Math.floor(rnd() * acts.length)]]); await g.step(1 + Math.floor(rnd() * 20));
  const t0 = performance.now(); const buf = await g.shot(); const t1 = performance.now();
  const r = await (await fetch(EYE + "/perceive", { method: "POST", body: buf })).json(); const t2 = performance.now();
  if (r.retry || !r.player) { await g.act(["r"], 2); await g.step(60); await fetch(EYE + "/reset", { method: "POST" }); }
  if (i < 20) continue;   // 暖機
  const T = r.timing_ms || {}; const server = Object.values(T).reduce((a, b) => a + b, 0);
  rows.push({ i: i - 20, capture_ms: +(t1 - t0).toFixed(2), perceive_rtt_ms: +(t2 - t1).toFixed(2), eye_total_ms: +(t2 - t0).toFixed(2),
    server_ms: +server.toFixed(2), ...Object.fromEntries(Object.entries(T).map(([k, v]) => ["srv_" + k, v])), png_bytes: buf.length, player: r.player ? 1 : 0 });
}
await g.close();
fs.mkdirSync("data/bench", { recursive: true });
const stamp = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15);
const keys = Object.keys(rows[0]); fs.writeFileSync(`data/bench/eye_${stamp}.csv`, [keys.join(","), ...rows.map(r => keys.map(k => r[k]).join(","))].join("\n"));
const q = (k, p) => { const v = rows.map(r => r[k]).filter(x => typeof x === "number").sort((a, b) => a - b); return v[Math.min(v.length - 1, Math.floor(v.length * p))]; };
const summ = { n: rows.length, ...Object.fromEntries(keys.filter(k => k.endsWith("_ms")).map(k => [k, { p50: q(k, .5), p90: q(k, .9), p99: q(k, .99) }])), png_bytes_p50: q("png_bytes", .5) };
fs.writeFileSync(`data/bench/eye_${stamp}.json`, JSON.stringify(summ, null, 1)); console.log(JSON.stringify(summ));
