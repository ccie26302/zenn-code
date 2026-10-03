// 操作の効果を実測する(説明書づくり)。判断には使わない。
// 1) Z を押すコマ数とジャンプの高さ  2) 空中で左右を押したときの横移動  3) X・↑・↓・P・Space で何が起きるか
import { Owata } from "./owata.mjs";
import fs from "node:fs";
const EYE = "http://127.0.0.1:8099";
const OUT = new URL("../data/controls/", import.meta.url).pathname; fs.mkdirSync(OUT, { recursive: true });
const eye = async (b) => (await fetch(EYE + "/perceive", { method: "POST", body: b })).json();
const g = new Owata({}); await g.open(); await g.load();
if (!(await g.toGameplay()).ok) throw new Error("nav"); await g.resetAndFreeze();
const toStart = async () => { await g.act(["r"], 2); await g.step(60); await fetch(EYE + "/reset", { method: "POST" }); };
const track = async (frames) => { const ys = [], xs = []; for (let f = 0; f < frames; f++) { await g.step(1); const r = await eye(await g.shot()); if (r.player) { ys.push(r.player.y); xs.push(r.world.x); } } return { ys, xs }; };
const out = { jump: [], air: [], keys: [] };
// 1) 押す長さとジャンプの高さ(その場)
for (const hold of [1, 2, 4, 8, 12, 16, 24]) {
  await toStart(); const y0 = (await eye(await g.shot())).player.y;
  await g.page.keyboard.down("z"); const a = await track(hold); await g.page.keyboard.up("z"); const b = await track(70 - hold);
  const ys = [...a.ys, ...b.ys]; out.jump.push({ hold, peak_px: y0 - Math.min(...ys), air_frames: ys.filter(y => y < y0 - 2).length });
}
// 2) 空中の横移動: 跳んだあと、空中で右を押し続ける / 押さない
for (const [name, rightFrames] of [["空中で右を押さない", 0], ["空中で右を20コマ押す", 20], ["空中で右を40コマ押す", 40]]) {
  await toStart(); const x0 = (await eye(await g.shot())).world.x;
  await g.page.keyboard.down("z"); await g.step(12); await g.page.keyboard.up("z");
  if (rightFrames) { await g.page.keyboard.down("ArrowRight"); await track(rightFrames); await g.page.keyboard.up("ArrowRight"); }
  const r = await track(50 - rightFrames); out.air.push({ name, dx: (r.xs.at(-1) ?? x0) - x0 });
}
// 3) その他のキー
for (const k of ["x", "ArrowUp", "ArrowDown", "p", "Space", "Enter"]) {
  await toStart(); const before = await g.shot();
  await g.page.keyboard.down(k); await g.step(10); const during = await g.shot(); await g.page.keyboard.up(k); await g.step(20); const after = await g.shot();
  fs.writeFileSync(OUT + `key_${k}_during.png`, during); fs.writeFileSync(OUT + `key_${k}_after.png`, after);
  out.keys.push({ key: k, changed_during: Buffer.compare(before, during) !== 0, changed_after: Buffer.compare(before, after) !== 0 });
}
console.log(JSON.stringify(out, null, 1));
fs.writeFileSync(OUT + "controls.json", JSON.stringify(out, null, 1));
await g.close();
