// 2つ目の罠の板が作動する条件を調べる(判断には使わない)。(a) スタート地点で 400 コマ待つ (b) 崖際まで歩いて 300 コマ待つ
import { Owata } from "./owata.mjs";
const EYE = "http://127.0.0.1:8099";
const eye = async (b) => (await fetch(EYE + "/perceive", { method: "POST", body: b })).json();
const g = new Owata({}); await g.open(); await g.load();
if (!(await g.toGameplay()).ok) throw new Error("nav"); await g.resetAndFreeze();
for (const [name, walk] of [["スタートで待つ", 0], ["崖際で待つ", 26]]) {
  await g.act(["r"], 2); await g.step(60); await fetch(EYE + "/reset", { method: "POST" });
  await g.page.keyboard.down("ArrowRight"); for (let f = 0; f < walk; f++) await g.step(1); await g.page.keyboard.up("ArrowRight");
  let first = null, plat = null, x = null;
  for (let f = 0; f < 400; f++) { await g.step(1); const r = await eye(await g.shot()); x = r.world?.x ?? x; if (!first && (r.press || []).length) { first = f; break; } }
  console.log(name, "自機 x", x, "板が見えたコマ", first);
}
await g.close();
