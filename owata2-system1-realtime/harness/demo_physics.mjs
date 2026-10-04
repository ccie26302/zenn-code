// 参考デモ方式のハーネスの物理と予測(run_demo.mjs と検証用スクリプトで共有)。
// すべて実測から決めた値(data/controls/physics.json、録画からの計測)。座標は世界座標、高さ dy は足元が地面(スタートの地面)から何 px 上か。
export const PH = {
  RISE_FRAMES: 12, V0: 6.7, G_HELD: 0.3, G_REL: 0.5, G_FALL: 0.38, VY_MIN: -10, VX_AIR: 3, VX_WALK: 2.73,
  PL_MIN: 198, PL_MAX: 320, PL_W: 55, PL_SPEED: 2, PL_DY: 71,               // 動く足場
  CLIFF_X: 185, FAR_X: 390, FAR_EDGE: 386, GROUND_Y: 302,                   // 崖の端・向こう岸
  HALF_W: 23, BODY_H: 27,                                                   // 自機の体
  TR_X0: 187, TR_X1: 392, TR_TRIGGER_X: 279, TR_DELAY: 1, TR_Y_REST: 357, TR_Y_UP: 217, TR_RISE: 10, TR_HOLD: 90, TR_LOWER: 2,   // せり上がるトゲの床(1つ目の罠)
  PR_X0: 423, PR_X1: 527, PR_TOP: 30, PR_TRIGGER_X: 395, PR_DELAY: 9, PR_Y0: 8, PR_V0: 3, PR_ACC: 0.45, PR_GROUND_Y: 313, FEET_Y: 315,   // 下りてくる板
};
export const ACTS = ["noop", "right", "right_jump", "jump", "left", "left_jump"];
export const KEYS = { noop: [], right: ["ArrowRight"], right_jump: ["z", "ArrowRight"], jump: ["z"], left: ["ArrowLeft"], left_jump: ["z", "ArrowLeft"] };
export const isJump = (a) => a.endsWith("jump");
export const onPlat = (x, p) => x >= p.x0 - 4 && x <= p.x0 + PH.PL_W + 4;
// 板の範囲に体がかかっているか(中心 x で)
export const inPressX = (x) => x + PH.HALF_W > PH.PR_X0 && x - PH.HALF_W < PH.PR_X1;
export const PRESS_SAFE_LEFT = [PH.FAR_EDGE + 2, PH.PR_X0 - PH.HALF_W - 1];   // 板が下りても当たらない向こう岸の左の狭い場所
export const PRESS_SAFE_RIGHT_FROM = PH.PR_X1 + PH.HALF_W + 1;

// トゲの床: {state: 'idle'|'armed'|'rising'|'up'|'lowering', t, y(画面上のトゲの底辺)}。足場に初めて着地すると作動
export function stepTrap(tr) {
  if (tr.state === "armed" && ++tr.t >= PH.TR_DELAY) { tr.state = "rising"; }
  else if (tr.state === "rising") { tr.y = Math.max(PH.TR_Y_UP, tr.y - PH.TR_RISE); if (tr.y <= PH.TR_Y_UP) { tr.state = "up"; tr.t = 0; } }
  else if (tr.state === "up" && ++tr.t >= PH.TR_HOLD) { tr.state = "lowering"; }
  else if (tr.state === "lowering") { tr.y = Math.min(PH.TR_Y_REST, tr.y + PH.TR_LOWER); if (tr.y >= PH.TR_Y_REST) tr.state = "spent"; }
}
export const trapTipDy = (tr) => PH.FEET_Y - ((tr.y ?? PH.TR_Y_REST) - 11);   // トゲの先が足元の線から何 px 上か
const trapHits = (s, tr) => ["rising", "up", "lowering"].includes(tr.state) && s.x + PH.HALF_W > PH.TR_X0 && s.x - PH.HALF_W < PH.TR_X1 && s.dy < trapTipDy(tr) && s.surf !== "far" && s.surf !== "near";
export function stepPlatform(p) { p.x0 += PH.PL_SPEED * p.dir; if (p.x0 >= PH.PL_MAX) { p.x0 = PH.PL_MAX; p.dir = -1; } else if (p.x0 <= PH.PL_MIN) { p.x0 = PH.PL_MIN; p.dir = 1; } }
// 板: {state: 'idle'|'armed'|'falling'|'down', t, y(画面上の▼の先), v}
export function stepPress(pr, s) {
  if (pr.state === "idle" && s.x >= PH.PR_TRIGGER_X) { pr.state = "armed"; pr.t = 0; }
  if (pr.state === "armed" && ++pr.t >= PH.PR_DELAY) { pr.state = "falling"; pr.y = PH.PR_Y0; pr.v = PH.PR_V0; }
  else if (pr.state === "falling") { pr.y += pr.v; pr.v += PH.PR_ACC; if (pr.y >= PH.PR_GROUND_Y) { pr.y = PH.PR_GROUND_Y; pr.state = "down"; } }
}
export const pressBottomDy = (pr) => pr.state === "falling" || pr.state === "down" ? PH.FEET_Y - pr.y : null;   // ▼の先が足元の線から何 px 上か
function pressHits(s, pr) {
  const b = pressBottomDy(pr);
  if (b == null || !inPressX(s.x)) return false;
  if (s.surf === "press_top") return false;
  return s.dy < b + PH.PR_TOP && s.dy + PH.BODY_H > b;   // 体の縦の範囲と、板(▼の先〜上面)の縦の範囲が重なる
}
// 1コマ進める。戻り値: 着地・落下・死亡の出来事(なければ null)
export function stepPlayer(s, p, pr, keys) {
  const R = keys.has("ArrowRight"), L = keys.has("ArrowLeft"), Z = keys.has("z");
  if (s.surf) {
    s.x += (R ? PH.VX_WALK : 0) - (L ? PH.VX_WALK : 0) + (s.surf === "platform" ? PH.PL_SPEED * p.dir : 0);
    if (Z && !s.zPrev) { s.surf = null; s.vy = PH.V0; s.zh = 1; s.dy += s.vy; }
    else if (s.surf === "near" && s.x > PH.CLIFF_X) { s.surf = null; s.vy = 0; }
    else if (s.surf === "platform" && !onPlat(s.x, p)) { s.surf = null; s.vy = 0; }
    else if (s.surf === "far" && s.x < PH.FAR_EDGE) { s.surf = null; s.vy = 0; }
    else if (s.surf === "press_top" && !(s.x >= PH.PR_X0 - 10 && s.x <= PH.PR_X1 + 10)) { s.surf = null; s.vy = 0; }
  } else {
    s.x += (R ? PH.VX_AIR : 0) - (L ? PH.VX_AIR : 0);
    if (Z && s.zh > 0 && s.zh < PH.RISE_FRAMES && s.vy > 0) { s.vy = PH.V0; s.zh++; }
    else { if (!Z) s.zh = 0; s.vy = Math.max(s.vy - (s.vy > 0 ? (Z ? PH.G_HELD : PH.G_REL) : PH.G_FALL), PH.VY_MIN); }
    const prev = s.dy; s.dy += s.vy;
    if (s.vy < 0 && prev >= PH.PL_DY && s.dy <= PH.PL_DY && onPlat(s.x, p)) { s.dy = PH.PL_DY; s.vy = 0; s.surf = "platform"; s.zPrev = Z; return "platform"; }
    if (s.vy < 0 && pr.state === "down" && prev >= PH.PR_TOP && s.dy <= PH.PR_TOP && s.x >= PH.PR_X0 - 10 && s.x <= PH.PR_X1 + 10) { s.dy = PH.PR_TOP; s.vy = 0; s.surf = "press_top"; s.zPrev = Z; return "press_top"; }
    if (s.dy <= 0) { s.dy = 0; s.vy = 0; if (s.x <= PH.CLIFF_X) { s.surf = "near"; s.zPrev = Z; return "near_ground"; } if (s.x >= PH.FAR_EDGE) { s.surf = "far"; s.zPrev = Z; return "far_ground"; } return "pit"; }
  }
  s.zPrev = Z;
  return null;
}
const SURF_NAME = { near: "near_ground", far: "far_ground", platform: "platform", press_top: "press_top" };
// 今の状態から、前回の操作を lag コマ続け、そのあと action を押し続けたときの最初の出来事。
// 地上で跳ばない操作は次の判断で変えられるので見る範囲を短くする(shortHorizon)。跳ぶ操作と空中では着地まで見る。
// 着地したあと、板が下りてきて当たるなら press と返す(着地点が板の下)
export function predict(st, lag, prevAction, action, shortHorizon = 16) {
  const s = { ...st.self }, p = { ...st.plat }, pr = { ...st.press }, tr = { ...(st.trap || { state: "idle", t: 0, y: PH.TR_Y_REST }) };
  const committed = isJump(action) || !s.surf;
  const horizon = committed ? 120 : shortHorizon;
  let landed = null;
  for (let f = 1; f <= lag + horizon; f++) {
    // 着地後は、板の範囲にいれば左の安全地帯へ歩いて戻り、そこで待つとみなす(着地後の次の判断でそうできるので)
    const retreat = landed && pr.state !== "down" && s.surf === "far" && s.x > PRESS_SAFE_LEFT[1];
    const keys = new Set(f <= lag ? KEYS[prevAction] : landed ? (retreat ? ["ArrowLeft"] : []) : KEYS[action]);
    if (f === lag + 1 && isJump(action) && s.surf) keys.delete("z");   // 押し直しのために1コマ離す
    stepPlatform(p); stepPress(pr, s); stepTrap(tr);
    const ev = stepPlayer(s, p, pr, keys);
    if (s.surf === "platform" && s.x >= PH.TR_TRIGGER_X && tr.state === "idle") { tr.state = "armed"; tr.t = 0; tr.y = PH.TR_Y_REST; }   // 足場の上で x≥279 に来ると作動(録画から)
    if (trapHits(s, tr)) return { surface: "spikes", frames: f, x: Math.round(s.x) };
    if (pressHits(s, pr)) return { surface: "press", frames: f, x: Math.round(s.x) };
    if (ev === "pit") return { surface: "pit", frames: f, x: Math.round(s.x) };
    if (ev && f > lag && !landed) {
      landed = { surface: ev, frames: f, x: Math.round(s.x) };
      if (ev === "platform" && s.x >= PH.TR_TRIGGER_X && tr.state === "armed") landed.triggers_spike_floor = true;   // この着地でトゲの床が作動する
      if (!(ev === "far_ground" && pr.state !== "down" && inPressX(s.x))) return landed;   // 板の下でなければ着地で確定
      landed.then = "retreat_left_to_safe_waiting_x";
    }
    if (landed && pr.state === "down") return { ...landed, surface: landed.surface, crushed: false };
  }
  if (landed) return landed;
  if (s.surf) return { surface: `stays_on_${SURF_NAME[s.surf]}`, frames: null, x_after: Math.round(s.x) };
  return { surface: "airborne", frames: null };
}
export function trapFacts(tr) {
  return { state: { idle: "not_triggered", armed: "triggered", rising: "rising", up: "up", lowering: "lowering", spent: "lowered" }[tr.state] ?? tr.state,
    trigger: `standing on the platform at x >= ${PH.TR_TRIGGER_X}`, zone_x: [PH.TR_X0, PH.TR_X1], spike_tips_height_above_ground_px: Math.round(trapTipDy(tr)),
    note: "When up, the spikes reach above the platform; anything over the pit lower than the tips dies." };
}
export function landingFacts(st, lag, prevAction, DECISION_FRAMES = 8) {
  const ifNow = Object.fromEntries(ACTS.map(a => [a, predict(st, lag, prevAction, a, DECISION_FRAMES + lag)]));
  const safe = (r) => ["platform", "far_ground", "press_top"].includes(r.surface);
  let untilSafe = null;
  if (st.self.surf === "near") for (let w = 0; w <= 130; w += 2) { if (safe(predict(st, lag + w, w === 0 ? prevAction : "noop", "right_jump"))) { untilSafe = w; break; } }
  const later = predict(st, lag + DECISION_FRAMES, "noop", "right_jump");
  return { if_chosen_now: ifNow, takeoff_window_closes_this_decision: safe(ifNow.right_jump) && !safe(later), frames_until_safe_takeoff: untilSafe };
}
// 板の事実(目で見えた値があればそれ、なければ記憶している作動の状態から)
export function pressFacts(pr, x) {
  const b = pressBottomDy(pr);
  let framesUntilDown = null;
  if (pr.state === "falling") { const q = { ...pr }; let n = 0; while (q.state !== "down" && n < 200) { stepPress(q, { x: 0 }); n++; } framesUntilDown = n; }
  if (pr.state === "armed") framesUntilDown = (PH.PR_DELAY - pr.t) + 30;
  return {
    state: { idle: "not_triggered", armed: "triggered_not_visible_yet", falling: "descending", down: "down_on_ground" }[pr.state],
    trigger: `drops when the character passes x=${PH.PR_TRIGGER_X}`,
    zone_x: [PH.PR_X0, PH.PR_X1], left_edge_relative_px: PH.PR_X0 - x, right_edge_relative_px: PH.PR_X1 - x,
    bottom_height_above_ground_px: b == null ? null : Math.round(b), frames_until_down: framesUntilDown,
    character_overlaps_zone: inPressX(x),
    safe_waiting_x: PRESS_SAFE_LEFT, safe_beyond_x_from: PRESS_SAFE_RIGHT_FROM,
    top_height_above_ground_px: PH.PR_TOP, can_stand_on_top_when_down: true,
  };
}

// ---------- 探索の補助(参考デモの「先読み探索」に当たる) ----------
// 8コマごとに操作を選ぶ列(最大 depth 段)を物理の式で試し、死なず・トゲの床を作動させず・いちばん先へ進める列を返す。
// 1段ずつ進めて死んだ枝は打ち切る。最後の段は着地するまでその操作を続けてから評価する。
const PLAN_ACTS = ["right_jump", "right", "noop", "left"];
const clone = (w) => ({ s: { ...w.s }, p: { ...w.p }, pr: { ...w.pr }, tr: { ...w.tr }, prevAct: w.prevAct });
function advance(w, act, frames, firstOfStep) {
  for (let f = 0; f < frames; f++) {
    const keys = new Set(KEYS[act]);
    if (f === 0 && firstOfStep && act !== w.prevAct && isJump(act) && w.s.surf) keys.delete("z");
    stepPlatform(w.p); stepPress(w.pr, w.s); stepTrap(w.tr);
    const ev = stepPlayer(w.s, w.p, w.pr, keys);
    if (w.s.surf === "platform" && w.s.x >= PH.TR_TRIGGER_X && w.tr.state === "idle") return "triggers_spike_floor";
    if (trapHits(w.s, w.tr)) return "spikes";
    if (pressHits(w.s, w.pr)) return "press";
    if (ev === "pit") return "pit";
  }
  if (firstOfStep) w.prevAct = act;
  return null;
}
function scoreWorld(w) {
  const { s, pr } = w;
  let tier = { near: 1, platform: 2, far: 3, press_top: 5 }[s.surf] ?? 0;
  if (s.surf === "far" && ((pr.state === "down" && !inPressX(s.x)) || (s.x >= PRESS_SAFE_LEFT[0] && s.x <= PRESS_SAFE_LEFT[1]))) tier = 4;
  if (s.surf === "far" && s.x >= PRESS_SAFE_RIGHT_FROM) tier = 6;
  return tier * 10000 + s.x;
}
export function searchPlan(st, lag, prevAction, step = 8, depth = 7) {
  const w0 = { s: { ...st.self }, p: { ...st.plat }, pr: { ...st.press }, tr: { ...(st.trap || { state: "idle", t: 0, y: PH.TR_Y_REST }) }, prevAct: prevAction };
  if (advance(w0, prevAction, lag, false)) return { recommended_first_action: null, plan: null, note: "death is already unavoidable during the reaction delay" };
  let best = null, n = 0;
  const rec = (w, plan) => {
    if (plan.length === depth || (plan.length > 0 && w.s.surf && scoreWorld(w) >= 60000)) {
      const v = clone(w); let dead = null, k = 0;
      while (!v.s.surf && k < 90 && !dead) { dead = advance(v, plan.at(-1), 1, false); k++; }   // 着地まで続ける
      n++;
      if (dead || !v.s.surf) return;
      // 板の範囲で終わるなら、左の安全地帯へ戻って板が下りるまで待てるかを確かめる
      if (v.s.surf === "far" && v.pr.state !== "down" && inPressX(v.s.x)) {
        let kk = 0; while (v.pr.state !== "down" && kk < 80 && !dead) { dead = advance(v, v.s.x > PRESS_SAFE_LEFT[1] ? "left" : "noop", 1, false); kk++; }
        if (dead) return;
      }
      const sc = scoreWorld(v) - plan.length;   // 同点なら短い列
      if (!best || sc > best.score) best = { plan: [...plan], score: sc, end: { x: Math.round(v.s.x), surface: { near: "near_ground", far: "far_ground", platform: "platform", press_top: "press_top" }[v.s.surf] } };
      return;
    }
    for (const a of PLAN_ACTS) { const v = clone(w); if (advance(v, a, step, true)) continue; plan.push(a); rec(v, plan); plan.pop(); }
  };
  rec(w0, []);
  return best ? { recommended_first_action: best.plan[0], plan: best.plan, plan_step_frames: step, plan_end: best.end, plans_evaluated: n }
              : { recommended_first_action: null, plan: null, plans_evaluated: n, note: "no plan avoids death" };
}
