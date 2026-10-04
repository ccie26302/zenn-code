// 参考デモ方式のハーネス用に、予測の元になる物理を実測する(判断には使わない。予測表を作るだけ)。
// 1) 足場: スタート地点で止まったまま 360 コマ、世界座標の左端と向き
// 2) 押しっぱなしの跳び方: スタート地点から [Z+→ を k コマ押してから → だけ] / [Z+→ を k コマ押してから何も押さない] の軌跡(dx, dy)を1コマずつ
// 3) 歩く速さ: → を押し続けて 30 コマ
// 出力: data/controls/physics.json
import { Owata } from "./owata.mjs";
import fs from "node:fs";
const EYE = "http://127.0.0.1:8099";
const eye = async (b) => (await fetch(EYE + "/perceive", { method: "POST", body: b })).json();
const g = new Owata({}); await g.open(); await g.load();
if (!(await g.toGameplay()).ok) throw new Error("nav"); await g.resetAndFreeze();
const toStart = async () => { await g.act(["r"], 2); await g.step(60); await fetch(EYE + "/reset", { method: "POST" }); return eye(await g.shot()); };
const out = { platform: [], jumps: {}, walk: [] };

// 1) 足場
{ const r0 = await toStart();
  for (let f = 0; f < 360; f++) { await g.step(1); const r = await eye(await g.shot()); if (r.platform) out.platform.push({ f, wx0: r.platform.x0 + r.cam.x, wx1: r.platform.x1 + r.cam.x, y0: r.platform.y0, moving: r.platform.moving }); }
  out.start = { x: r0.world.x, y: r0.world.y, feet: r0.player.box[3] }; }

// 2) 跳び方
for (const [name, holdZ, after] of [["zr16_then_r", 16, ["ArrowRight"]], ["zr16_then_none", 16, []], ["zr8_then_r", 8, ["ArrowRight"]], ["z16_then_none", 16, null]]) {
  const r0 = await toStart(); const x0 = r0.world.x, y0 = r0.world.y;
  const keys = after === null ? ["z"] : ["z", "ArrowRight"];
  for (const k of keys) await g.page.keyboard.down(k);
  const tr = [];
  for (let f = 1; f <= 90; f++) {
    if (f === holdZ + 1) { for (const k of keys) await g.page.keyboard.up(k); for (const k of (after || [])) await g.page.keyboard.down(k); }
    await g.step(1); const r = await eye(await g.shot());
    if (!r.player) break;
    tr.push({ f, dx: r.world.x - x0, dy: y0 - r.world.y, grounded: !!r.ground?.on_ground });
    if (f > holdZ + 2 && r.ground?.on_ground) break;
  }
  for (const k of ["z", "ArrowRight"]) await g.page.keyboard.up(k);
  out.jumps[name] = tr;
}

// 3) 歩く速さ
{ const r0 = await toStart(); await g.page.keyboard.down("ArrowRight");
  for (let f = 1; f <= 30; f++) { await g.step(1); const r = await eye(await g.shot()); if (r.player) out.walk.push({ f, dx: r.world.x - r0.world.x }); }
  await g.page.keyboard.up("ArrowRight"); }

const xs = out.platform.map(p => p.wx0);
const speeds = out.platform.slice(1).map((p, i) => Math.abs(p.wx0 - out.platform[i].wx0)).filter(v => v > 0);
out.summary = { platform_wx0_min: Math.min(...xs), platform_wx0_max: Math.max(...xs), platform_y0: out.platform[0]?.y0,
  platform_speed_median: speeds.sort((a, b) => a - b)[Math.floor(speeds.length / 2)],
  jump_peak: Object.fromEntries(Object.entries(out.jumps).map(([k, t]) => [k, Math.max(...t.map(p => p.dy))])),
  jump_land_dx: Object.fromEntries(Object.entries(out.jumps).map(([k, t]) => [k, t.at(-1)?.dx])),
  walk_px_per_frame: out.walk.at(-1) ? +(out.walk.at(-1).dx / out.walk.at(-1).f).toFixed(2) : null };
console.log(JSON.stringify(out.summary));
fs.writeFileSync(new URL("../data/controls/physics.json", import.meta.url).pathname, JSON.stringify(out, null, 1));
await g.close();
