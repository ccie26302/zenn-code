// 土台の確認(修正 B4): 新しい11択の組み合わせで、1面の足場に乗れる列が存在するか(総当たり)。判断には使わない。
import { Owata, ACTIONS2 } from "./owata.mjs";
import fs from "node:fs";
const EYE = "http://127.0.0.1:8099";
const eye = async (b) => (await fetch(EYE + "/perceive", { method: "POST", body: b })).json();
const g = new Owata({}); await g.open(); await g.load();
if (!(await g.toGameplay()).ok) throw new Error("nav"); await g.resetAndFreeze();
const res = [];
for (let w = 0; w <= 120; w += 4) for (const n of [0, 1, 2, 3]) {
  await g.act(["r"], 2); await g.step(60); await fetch(EYE + "/reset", { method: "POST" });
  let r = await eye(await g.shot());
  for (let i = 0; i < 12 && r.player && r.world.x < 165; i++) { await g.actSpec(ACTIONS2.right); r = await eye(await g.shot()); }
  await g.step(w);
  await g.actSpec(ACTIONS2.rightjump_big);
  for (let i = 0; i < n; i++) await g.actSpec(ACTIONS2.right);
  // 着地を待ちながら、足場の上に立ったかを見る
  let landed = null, died = false;
  for (let f = 0; f < 60; f++) {
    await g.step(1); r = await eye(await g.shot());
    if (!r.player) { died = true; break; }
    if (r.ground?.on_ground && r.world.x >= 200 && r.world.x <= 380 && r.player.y < 280) { landed = { x: r.world.x, y: r.player.y, f }; break; }
  }
  res.push({ w, n, landed, died });
  if (landed) console.log(`乗れた: 待ち${w}コマ・空中で右${n}回 → x=${landed.x} y=${landed.y}`);
}
const ok = res.filter(r => r.landed);
console.log(`足場に乗れた組み合わせ: ${ok.length}/${res.length}`);
fs.writeFileSync(new URL("../data/controls/feasible.json", import.meta.url).pathname, JSON.stringify(res, null, 1));
await g.close();
