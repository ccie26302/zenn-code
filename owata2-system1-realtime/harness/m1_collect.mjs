// M1: 目の評価用に、いろいろな場面の画面を集める(1面のみ・ランダム行動、乱数種固定)。
// 各コマに「直前の行動」「エピソード内ステップ」「自爆したか」を記録。正解ラベルは後で目視で付ける。
import { Owata, ACTIONS } from "./owata.mjs";
import fs from "node:fs";

const OUT = new URL("../data/m1/frames/", import.meta.url).pathname; fs.mkdirSync(OUT, { recursive: true });
const EPISODES = Number(process.env.EP || 6), STEPS = Number(process.env.STEPS || 30);
let s = 20261002; const rnd = () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
const POOL = ["right", "right", "right", "rightjump", "rightjump", "jump", "left", "wait", "leftjump"];
const g = new Owata({});
await g.open(); await g.load();
const nav = await g.toGameplay(); if (!nav.ok) throw new Error("nav failed");
await g.resetAndFreeze();
const meta = [];
let id = 0;
const save = async (ep, st, action) => {
  const f = `f${String(id).padStart(4, "0")}.png`; fs.writeFileSync(OUT + f, await g.shot());
  meta.push({ id, file: f, ep, step: st, action }); id++;
};
// 背景(自機なし)を先に作る: 自爆して少し待つ
await g.act(["Escape"], 2); await g.step(150);
fs.writeFileSync(new URL("../data/m1/bg.png", import.meta.url).pathname, await g.shot());
await g.act(["r"], 2); await g.step(60);
for (let ep = 0; ep < EPISODES; ep++) {
  await save(ep, 0, "start");
  for (let st = 1; st <= STEPS; st++) {
    const a = ep === EPISODES - 1 && st === 10 ? "suicide" : POOL[Math.floor(rnd() * POOL.length)];
    if (a === "suicide") await g.act(["Escape"], 2); else await g.act(ACTIONS[a], 6 + Math.floor(rnd() * 6));
    await save(ep, st, a);
  }
  await g.act(["r"], 2); await g.step(60);
}
fs.writeFileSync(new URL("../data/m1/frames.json", import.meta.url).pathname, JSON.stringify(meta, null, 1));
console.log("frames:", meta.length);
await g.close();
