// 空中で Z を押し直すと、もう一度跳べるか(何回まで)を実測する。判断には使わない。
import { Owata } from "./owata.mjs";
const EYE = "http://127.0.0.1:8099";
const eye = async (b) => (await fetch(EYE + "/perceive", { method: "POST", body: b })).json();
const g = new Owata({}); await g.open(); await g.load();
if (!(await g.toGameplay()).ok) throw new Error("nav"); await g.resetAndFreeze();
await g.act(["r"], 2); await g.step(60); await fetch(EYE + "/reset", { method: "POST" });
const r0 = await eye(await g.shot()); const y0 = r0.world.y;
const tr = [];
// 跳ぶ → 10コマ押す → 2コマ離す → また押す … を4回。左右は押さない(その場)
for (let k = 0; k < 4; k++) {
  await g.page.keyboard.down("z");
  for (let f = 0; f < 10; f++) { await g.step(1); const r = await eye(await g.shot()); tr.push(r.player ? y0 - r.world.y : null); }
  await g.page.keyboard.up("z");
  for (let f = 0; f < 2; f++) { await g.step(1); const r = await eye(await g.shot()); tr.push(r.player ? y0 - r.world.y : null); }
}
for (let f = 0; f < 80; f++) { await g.step(1); const r = await eye(await g.shot()); tr.push(r.player ? y0 - r.world.y : null); if (r.ground?.on_ground && f > 5) break; }
console.log(JSON.stringify(tr));
await g.close();
