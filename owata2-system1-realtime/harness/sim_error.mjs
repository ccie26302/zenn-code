// 物理の式の誤差: 各判断の時点の状態から、実際に押した操作の列をなぞって計算し、実際の位置(x, 高さ)と比べる(30コマ先まで)
import fs from "node:fs";
import { PH, KEYS, isJump, stepPlatform, stepPress, stepPlayer, stepTrap } from "./demo_physics.mjs";
const tags = process.argv.slice(2);
const errs = { 5: [], 10: [], 20: [], 30: [] }; const surfOk = [0, 0];
for (const tag of tags) {
  const eps = fs.readFileSync(new URL(`../data/play/${tag}/episodes.jsonl`, import.meta.url).pathname, "utf8").trim().split("\n").map(JSON.parse);
  for (const e of eps) {
    const F = e.framesLog;
    for (const d of e.decisionsLog) {
      const s0 = d.state, f0 = d.frame;
      if (!F[f0] || F[f0].x == null || d.state.player.height_above_ground_px < -3) continue;
      const s = { x: s0.player.x, dy: Math.max(0, s0.player.height_above_ground_px), vy: s0.player.grounded ? 0 : s0.player.vertical_speed_px_per_frame,
        surf: { near_ground: "near", far_ground: "far", platform: "platform", press_top: "press_top" }[s0.player.standing_on] ?? null, zh: 0, zPrev: KEYS[F[Math.max(0, f0 - 1)].held].includes("z") };
      if (!s.surf && s.vy > 0 && s.zPrev) s.zh = s0.trajectory.airborne_frames;
      const p = { x0: (s0.platform.left_edge_relative_px ?? 0) + s0.player.x, dir: s0.platform.direction === "left" ? -1 : 1 };
      const pr = { state: "idle", t: 0 }, tr = { state: "idle", t: 0, y: PH.TR_Y_REST };
      let prevHeld = F[Math.max(0, f0 - 1)].held;
      for (let k = 1; k <= 30 && f0 + k < F.length; k++) {
        const held = F[f0 + k - 1].held; const keys = new Set(KEYS[held]);
        if (held !== prevHeld && isJump(held) && s.surf) keys.delete("z");
        prevHeld = held;
        stepPlatform(p); stepPress(pr, s); stepTrap(tr); stepPlayer(s, p, pr, keys);
        const real = F[f0 + k];
        if (real.x == null) break;
        if (errs[k]) errs[k].push([Math.abs(s.x - real.x), Math.abs(s.dy - real.dy)]);
        if (k === 30) { surfOk[1]++; surfOk[0] += (s.surf ?? "air") === (real.surf ?? "air"); }
      }
    }
  }
}
const q = (v, p) => v.sort((a, b) => a - b)[Math.floor(v.length * p)];
for (const [k, v] of Object.entries(errs)) console.log(`${k}コマ先 N=${v.length}: x誤差 p50 ${q(v.map(a => a[0]), .5)?.toFixed(1)} p90 ${q(v.map(a => a[0]), .9)?.toFixed(1)} / 高さ誤差 p50 ${q(v.map(a => a[1]), .5)?.toFixed(1)} p90 ${q(v.map(a => a[1]), .9)?.toFixed(1)}`);
console.log(`30コマ先の接地面の一致 ${surfOk[0]}/${surfOk[1]}`);
