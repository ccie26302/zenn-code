// M1: 集めたコマに v1 / v2 の目を当てて、予測を JSON に書く
import fs from "node:fs";
import { makeBackground, perceive, makeBackground2, perceive2, perceive3, makePlatformTemplate } from "./perceive.mjs";
const D = new URL("../data/m1/", import.meta.url).pathname;
const meta = JSON.parse(fs.readFileSync(D + "frames.json"));
const bgBuf = fs.readFileSync(D + "bg.png");
const bg1 = makeBackground(bgBuf), bg2 = makeBackground2(bgBuf), tpl = makePlatformTemplate(bgBuf);
for (const m of meta) {
  const b = fs.readFileSync(D + "frames/" + m.file);
  const p1 = perceive(b, bg1), p2 = perceive2(b, bg2), p3 = perceive3(b, bg2, tpl);
  m.v1 = p1.player ? { x: p1.player.x, y: p1.player.y } : null;
  m.v2 = p2.player ? p2.player : null;
  m.v3 = p3.player ? p3.player : null; m.plat = p3.platform;
  m.retry = p2.retry;
}
fs.writeFileSync(D + "pred.json", JSON.stringify(meta, null, 1));
const n = meta.length, a1 = meta.filter(m => m.v1).length, a2 = meta.filter(m => m.v2).length;
console.log(`frames ${n}: v1 自機あり ${a1} / v2 ${a2} / v3 ${meta.filter(m => m.v3).length} / 足場検出 ${meta.filter(m => m.plat).length} / R:Retry ${meta.filter(m => m.retry).length}`);
