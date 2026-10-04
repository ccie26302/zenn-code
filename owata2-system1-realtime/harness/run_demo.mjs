// 参考デモ方式のハーネス(fhshaik/typesafe-mario の設計を『人生オワタの大冒険2』1面の最初の穴に当てはめて書き直したもの。コードは流用していない)。
// 参考デモの考え方:
//  - 状態は文章ではなく、意味ごとにまとめた JSON。タイミングの計算はコードで行い、「事実」として渡す(着地の予測・跳べる時間の終わり)
//  - 指示文に判断のルールを書く。どの操作を選ぶかはモデル(Choice の1位をそのまま実行。ハーネスは上書きしない)
//  - 操作は押しっぱなし。答えを待つ間も前回の操作を押し続け、ゲームは止めない。8コマごとに次を問い合わせる
//  - 地上で新しくジャンプを選んだら、1コマだけ Z を離して押し直す
//  - 記憶なし
// POLICY=systemone(MODEL_URL) / rules(モデルなし。同じ予測から機械的に選ぶ対照) / facts(事実だけ渡し、ルールの指示を外す対照)
//        / labeled・labeled2(選択肢に SAFE/DEATH の判定を書く) / rules_labeled2(labeled2 と同じ判定にモデルなしで従う対照)
//        LABEL_GOAL=1 で labeled2 の指示に「SAFE のおすすめが無ければ右へ進む SAFE を優先(ゴールは右)」を足す(右優先ルールと情報をそろえる)
// usage: POLICY=systemone MODEL_URL=http://127.0.0.1:8009/v1/systemone TAG=demo_kev_1 EP=100 REC=1 node run_demo.mjs
import { Owata } from "./owata.mjs";
import fs from "node:fs";
import { PH, ACTS, KEYS, isJump, onPlat, landingFacts, stepPress, pressFacts, stepTrap, trapFacts, searchPlan, PRESS_SAFE_LEFT, PRESS_SAFE_RIGHT_FROM } from "./demo_physics.mjs";

const POLICY = process.env.POLICY || "rules", MODEL_URL = process.env.MODEL_URL || "", TAG = process.env.TAG || `demo_${POLICY}`;
const EPISODES = Number(process.env.EP || 30), MAX_FRAMES = Number(process.env.MAX_FRAMES || 1800), DECISION_FRAMES = Number(process.env.DECISION_FRAMES || 8);
const REC = process.env.REC === "1", GOAL_X = Number(process.env.GOAL_X || 600);
const FRAME_MS = 1000 / 60, EYE = process.env.EYE || "http://127.0.0.1:8099";
const OUT = new URL(`../data/play/${TAG}/`, import.meta.url).pathname; fs.mkdirSync(OUT, { recursive: true });

const DESC = {
  noop: "Release the controls. On the ground the character stays still (on the platform it rides along); in the air it falls straight down.",
  right: "Walk right without jumping; in the air, steer right.",
  right_jump: "Start a forward jump, or keep holding jump while rising to preserve height, steering right. Prefer this when `landing.if_chosen_now.right_jump.surface` is `platform` or `far_ground`, or when `landing.takeoff_window_closes_this_decision` is true.",
  jump: "Jump in place, or keep holding jump while rising without moving sideways.",
  left: "Walk left; in the air, steer left. Use it to wait for the platform or to recover from an overshoot.",
  left_jump: "Jump while moving left, or keep holding jump while rising, steering left.",
};
const INSTR_RULES = {
  question: "Which controller action should the character commit to next?",
  goal: "Cross the pit (land on the moving platform or on the far ground) and keep moving right without dying.",
  timing: `The selected action is held until the next decision, at least ${DECISION_FRAMES} frames.`,
  landing: "Use `landing.if_chosen_now`. Code has already accounted for inference delay, the previous action continuing until this choice takes effect, platform motion and jump physics. Choose an action whose predicted surface is `platform` or `far_ground`. Never choose an action whose predicted surface is `pit`.",
  approach: "On the near ground, walk `right` toward the cliff edge only while `landing.if_chosen_now.right.surface` is `stays_on_near_ground`; when it would be `pit`, stop with `noop` at the edge.",
  waiting: "At the cliff edge, if no forward jump is predicted to land safely, wait with `noop` instead of walking right; the platform comes back. `landing.frames_until_safe_takeoff` says when.",
  window: "If `landing.takeoff_window_closes_this_decision` is true, choose `right_jump` now; waiting one more decision misses the takeoff.",
  airborne: "While airborne and rising, keep `right_jump` held to preserve height. Keep the action whose prediction lands on the platform or the far ground. Do not switch to `noop` or `left` over the pit unless that prediction is the only safe one.",
  trap: "Standing on the platform at or right of `trap.trigger` x triggers `trap`: the spike floor of the pit rises above the platform within about 13 frames. Leave the platform toward the far ground before that. A prediction of `spikes` means death.",
  press: "`press` is a spiked block that drops onto the far ground inside `press.zone_x` after the character passes the trigger, and then stays down. Never be inside the zone before `press.state` is `down_on_ground`; wait at `press.safe_waiting_x`. A prediction of `press` means death. When it is down, jump onto its top (`press_top`) and then jump right past it.",
  search: "`search.recommended_first_action` is the first step of a plan found by code search over the physics (it avoids death and the spike-floor trigger). Prefer it unless a prediction shows it is unsafe.",
  delay: "`reaction_timing` describes how far the world moves before this choice takes effect. Judge from projected rather than current positions.",
};
const INSTR_FACTS = { question: INSTR_RULES.question, goal: INSTR_RULES.goal, timing: INSTR_RULES.timing };
const DESC_FACTS_UNUSED = 0;
const DESC_FACTS = Object.fromEntries(Object.entries(DESC).map(([k, v]) => [k, v.replace(/ Prefer this when[^]*$/, "").replace(/ Use it to[^]*$/, "")]));

// ---------- 目(毎コマ)と状態 ----------
const eye = async (buf) => (await fetch(EYE + "/perceive", { method: "POST", body: buf })).json();
const eyeReset = () => fetch(EYE + "/reset", { method: "POST" });
function makeTracker() { return { hist: [], airF: 0, takeoffX: null, missing: 0, best: -1e9, platDir: 1, lastPlat: null, press: { state: "idle", t: 0 }, trap: { state: "idle", t: 0, y: PH.TR_Y_REST }, lastX: null }; }
function track(T, r) {
  if (!r.player || r.retry) { T.missing++; return null; }
  T.missing = 0;
  const x = r.world.x, dy = PH.GROUND_Y - r.world.y, prev = T.hist.at(-1);
  // 速さは直近3コマの平均でならす(画面の1コマの揺れで、1コマ差だと 0 や 2倍になるため)
  const base = T.hist.length >= 3 ? T.hist.at(-3) : prev, nb = T.hist.length >= 3 ? 3 : 1;
  const vx = base ? (x - base.x) / nb : 0, vy = base ? (dy - base.dy) / nb : 0;
  let plat = null;
  if (r.platform) {
    const wx0 = r.platform.x0 + r.cam.x;
    if (T.lastPlat != null && wx0 !== T.lastPlat) T.platDir = wx0 > T.lastPlat ? 1 : -1;
    T.lastPlat = wx0; plat = { x0: wx0, dir: T.platDir };
  }
  const onPlatform = plat && Math.abs(dy - PH.PL_DY) <= 4 && onPlat(x, plat) && Math.abs(vy) <= 2;
  const grounded = !!r.ground?.on_ground || onPlatform;
  const surf = !grounded ? null : onPlatform ? "platform" : x >= PH.FAR_X ? "far" : "near";
  if (grounded) { T.airF = 0; T.takeoffX = null; } else { if (T.airF === 0) T.takeoffX = prev ? prev.x : x; T.airF++; }
  T.best = Math.max(T.best, x);
  // 板: 見えていれば目の値、見えていなければ作動の記憶から進める
  const pv = (r.press || [])[0];
  if (pv) { const y = pv.wy; T.press = { state: y >= PH.PR_GROUND_Y - 2 ? "down" : "falling", t: 0, y, v: T.press.y != null && T.press.state === "falling" ? Math.max(PH.PR_V0, y - T.press.y) : PH.PR_V0 }; }
  else if (T.press.state !== "down") stepPress(T.press, { x });
  T.lastX = x;
  // トゲの床: 目で見えるトゲの列(幅の広いもの)の高さで状態を決める。足場に乗ったら作動
  const spk = (r.spikes || []).find(q => q.x1 - q.x0 > 100);
  if (spk && spk.y < PH.TR_Y_REST - 3) { const prevY = T.trap.y; T.trap = { state: spk.y <= PH.TR_Y_UP + 3 ? "up" : spk.y < prevY ? "rising" : spk.y > prevY ? "lowering" : T.trap.state, t: T.trap.t + 1, y: spk.y }; }
  else if (T.trap.state === "idle" && onPlatform && x >= PH.TR_TRIGGER_X) T.trap = { state: "armed", t: 0, y: PH.TR_Y_REST };
  else if (T.trap.state === "armed") stepTrap(T.trap);
  const surf2 = grounded && T.press.state === "down" && Math.abs(dy - PH.PR_TOP) <= 4 && x >= PH.PR_X0 - 10 && x <= PH.PR_X1 + 10 ? "press_top" : surf;
  const o = { x, dy, vx, vy, grounded, surf: surf2, plat, spikes: r.spikes || [], player: r.player };
  T.hist.push(o); if (T.hist.length > 4) T.hist.shift();
  return o;
}
function buildState(o, T, lag, prevAction, prevInfo, frame) {
  const plat = o.plat || { x0: (PH.PL_MIN + PH.PL_MAX) / 2, dir: 1 };
  const st = { self: { x: o.x, dy: Math.max(0, o.dy), vy: o.grounded ? 0 : o.vy, surf: o.surf, zh: 0, zPrev: KEYS[prevAction].includes("z") }, plat: { ...plat }, press: { ...T.press }, trap: { ...T.trap } };
  if (!o.grounded && o.vy > 0 && KEYS[prevAction].includes("z")) st.self.zh = T.airF;   // 跳んでからのコマ数(12コマを過ぎていれば押し上げは効かない)
  const sp = o.spikes.find(q => q.x1 - q.x0 > 100);
  return { st, json: {
    objective: "Cross the pit to the far ground and keep moving right.",
    player: { x: o.x, height_above_ground_px: Math.round(o.dy), horizontal_speed_px_per_frame: o.vx, vertical_speed_px_per_frame: o.vy,
      grounded: o.grounded, standing_on: { near: "near_ground", far: "far_ground", platform: "platform", press_top: "press_top" }[o.surf] ?? null, jump_phase: o.grounded ? "grounded" : o.vy > 0 ? "rising" : "falling" },
    trajectory: { airborne_frames: T.airF, horizontal_distance_since_takeoff_px: T.takeoffX == null ? 0 : o.x - T.takeoffX, crossing_pit: !o.grounded && o.x > PH.CLIFF_X - 20 && o.x < PH.FAR_X },
    terrain: { cliff_edge_distance_px: o.x <= PH.CLIFF_X ? PH.CLIFF_X - o.x : null, pit_width_px: PH.FAR_X - PH.CLIFF_X, far_ground_distance_px: Math.max(0, PH.FAR_X - o.x), pit_has_spikes: true,
      observation_reliability: o.grounded ? "high" : "medium" },
    platform: o.plat ? { left_edge_relative_px: o.plat.x0 - o.x, right_edge_relative_px: o.plat.x0 + PH.PL_W - o.x, top_height_above_ground_px: PH.PL_DY,
      velocity_px_per_frame: PH.PL_SPEED * o.plat.dir, direction: o.plat.dir > 0 ? "right" : "left", travel_range_x: [PH.PL_MIN, PH.PL_MAX + PH.PL_W] } : { visible: false },
    landing: landingFacts(st, lag, prevAction, DECISION_FRAMES),
    search: process.env.SEARCH === "0" ? undefined : searchPlan(st, lag, prevAction, DECISION_FRAMES),
    press: pressFacts(T.press, o.x),
    trap: trapFacts(T.trap),
    reaction_timing: { action_horizon_frames: DECISION_FRAMES, last_inference_delay_frames: lag, total_reaction_horizon_frames: lag },
    recent_control: prevInfo,
    episode: { elapsed_frames: frame, best_x: T.best },
  } };
}

// ---------- 判断 ----------
async function decide(state) {
  if (POLICY === "rules") {
    // 参考デモの HeuristicPolicy に当たる検算用(モデルなし)。同じ事実から機械的に選ぶ
    if (state.search?.recommended_first_action && process.env.RULES_SEARCH !== "0") return { a: state.search.recommended_first_action, probs: null, noul: null, score: null, ms: 0 };
    const L = state.landing.if_chosen_now, P = state.player, PR = state.press;
    const SAFE = ["platform", "far_ground", "press_top"];
    const safe = (a) => SAFE.includes(L[a].surface) && !L[a].triggers_spike_floor;
    const stayX = (a) => String(L[a].surface).startsWith("stays_on") ? L[a].x_after : null;
    const inSafeLeft = (x) => x >= PRESS_SAFE_LEFT[0] && x <= PRESS_SAFE_LEFT[1];
    let a;
    if (P.grounded && P.standing_on === "near_ground") {
      if (safe("right_jump") && (state.terrain.cliff_edge_distance_px <= 40 || state.landing.takeoff_window_closes_this_decision)) a = "right_jump";
      else if (String(L.right.surface).startsWith("stays_on") && state.terrain.cliff_edge_distance_px > 12) a = "right";
      else a = "noop";
    } else if (P.grounded && P.standing_on === "platform") {
      const far = ["right_jump", "right", "jump", "noop"].filter(k => ["far_ground", "press_top"].includes(L[k].surface));
      a = far.length ? far.sort((u, v) => Math.abs(L[u].x - 394) - Math.abs(L[v].x - 394))[0]
        : state.trap.state === "not_triggered" && String(L.noop.surface).startsWith("stays_on") ? "noop" : (safe("right_jump") ? "right_jump" : "right");
    }
    else if (P.grounded && P.standing_on === "press_top") a = "right_jump";
    else if (P.grounded) {   // 向こう岸
      if (P.x >= PRESS_SAFE_RIGHT_FROM) a = "right";
      else if (PR.state === "down_on_ground") a = safe("right_jump") ? "right_jump" : "noop";
      else if (inSafeLeft(P.x)) a = "noop";
      else if (P.x > PRESS_SAFE_LEFT[1]) a = (stayX("left") != null && stayX("left") >= PRESS_SAFE_LEFT[0]) ? "left" : (String(L.left.surface) === "stays_on_far_ground" ? "left" : "noop");
      else a = (stayX("right") != null && stayX("right") <= PRESS_SAFE_LEFT[1]) ? "right" : "noop";
    } else {   // 空中
      const order = ["right_jump", "right", "noop", "jump", "left", "left_jump"];
      const far = order.filter(k => ["far_ground", "press_top"].includes(L[k].surface));                       // 向こう岸(板に当たらない着地。板の下なら戻る前提)
      const plat = state.trap.state === "not_triggered" ? order.filter(k => L[k].surface === "platform" && !L[k].triggers_spike_floor) : [];   // 罠を作動させない足場
      a = far.length ? (far.includes("right_jump") && P.jump_phase === "rising" ? "right_jump" : far.sort((u, v) => Math.abs(L[u].x - 394) - Math.abs(L[v].x - 394))[0])
        : plat.length ? plat[0] : (order.find(safe) || state.recent_control.action);
    }
    return { a, probs: null, noul: null, score: null, ms: 0 };
  }
  if (POLICY === "rules_labeled2") {
    // labeled2 と同じ判定を、モデルなしで指示どおりに機械的に選ぶ対照(査読の指摘を受けて追加)。
    // おすすめが SAFE ならおすすめ、そうでなければ SAFE の選択肢を ACTS の並び順で最初のもの、SAFE が無ければおすすめ(無ければ何もしない)
    const L = state.landing.if_chosen_now, rec = state.search?.recommended_first_action;
    const SAFE_S = ["platform", "far_ground", "press_top", "near_ground", "stays_on_near_ground", "stays_on_far_ground", "stays_on_platform", "stays_on_press_top"];
    const isSafe = (a) => SAFE_S.includes(L[a].surface) && !L[a].triggers_spike_floor;
    // RULES_ORDER=right なら、右へ進む操作から順に SAFE を探す(並び順の効果を見る対照)
    const ORDER = process.env.RULES_ORDER === "right" ? ["right_jump", "right", "jump", "noop", "left_jump", "left"] : ACTS;
    const a = rec && isSafe(rec) ? rec : (ORDER.find(isSafe) || rec || "noop");
    return { a, probs: null, noul: null, score: null, ms: 0 };
  }
  if (POLICY === "labeled2") {
    // 入力を作り直した版(2026-10-04、ユーザー指摘「ずっと同じ行動」を受けて): 状態は短い文章1つ、選択肢の先頭に SAFE/DEATH と探索のおすすめ。
    // 理由: laya は選択肢を48トークン・質問と選択肢を合計192トークン・全体512トークンで切り捨てる。kev は目的の文と「右へ進む結果を優先せよ」の指示に引っ張られていた可能性が高い(切り分けはしていない。kev の学習時の状態は最大7,552トークン)。
    const L = state.landing.if_chosen_now, rec = state.search?.recommended_first_action;
    const NAME = { noop: "do nothing", right: "walk right", right_jump: "jump right", jump: "jump in place", left: "walk left", left_jump: "jump left" };
    const SAY = { platform: ["SAFE", "lands on the moving platform"], far_ground: ["SAFE", "lands on the far ground"], press_top: ["SAFE", "lands on top of the press"], near_ground: ["SAFE", "lands back on the near ground"],
      pit: ["DEATH", "falls into the spike pit"], spikes: ["DEATH", "hits the rising spikes"], press: ["DEATH", "is crushed by the press"], stays_on_near_ground: ["SAFE", "stays on the near ground"],
      stays_on_far_ground: ["SAFE", "stays on the far ground"], stays_on_platform: ["SAFE", "stays on the platform"], stays_on_press_top: ["SAFE", "stays on the press"], airborne: ["UNKNOWN", "still in the air"] };
    const crit = Object.fromEntries(ACTS.map(a => { let [tag, txt] = SAY[L[a].surface] ?? ["UNKNOWN", L[a].surface];
      if (L[a].triggers_spike_floor) { tag = "DEATH"; txt = "lands on the platform and triggers the rising spikes"; }
      return [a, `${tag}${rec === a ? " (RECOMMENDED)" : ""}: ${NAME[a]}, ${txt}`]; }));
    const body = { state: "A side-scrolling game. Each option below was checked by a physics simulator that already accounts for the reaction delay, and is marked SAFE or DEATH.", model: "latest",
      questions: { next_action: { type: "choice", instructions: process.env.LABEL_GOAL === "1"
        ? "Choose an option marked SAFE. Never choose DEATH. Among SAFE options, prefer RECOMMENDED. If no SAFE option is RECOMMENDED, prefer a SAFE option that moves right, because the goal is to the right."
        : "Choose an option marked SAFE. Never choose DEATH. Among SAFE options, prefer RECOMMENDED.", criteria: crit } } };
    const t0 = performance.now();
    const r = await (await fetch(MODEL_URL, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) })).json();
    const ms = performance.now() - t0;
    const A = r.answers?.values || r.answers || {}; const c = A.next_action, probs = c.probabilities || {};
    const a = ACTS.includes(c.choice) ? c.choice : Object.keys(probs).sort((x, y) => probs[y] - probs[x])[0];
    return { a, probs, noul: null, score: null, ms, criteria: crit };
  }
  if (POLICY === "labeled") {
    // 予測を選択肢の説明に書く版(参考デモよりさらにハーネスが肩代わりする)。指示は短く、質問は1つ
    const L = state.landing.if_chosen_now;
    const say = (r) => ({ platform: "lands on the moving platform (safe for now)", far_ground: "lands on the far ground (safe)", press_top: "lands on top of the press (safe)",
      near_ground: "lands back on the near ground (safe, no progress)", pit: "falls into the spike pit (death)", spikes: "hits the rising spikes (death)", press: "is crushed by the press (death)",
      stays_on_near_ground: "stays on the near ground (safe)", stays_on_far_ground: "stays on the far ground (safe)", stays_on_platform: "stays on the platform (safe for now)", stays_on_press_top: "stays on the press (safe)", airborne: "still in the air" })[r.surface] ?? r.surface;
    const crit = Object.fromEntries(ACTS.map(a => [a, `${DESC_FACTS[a]} Predicted result: ${say(L[a])}${L[a].triggers_spike_floor ? " and triggers the rising spike floor (death)" : ""}${state.search?.recommended_first_action === a ? " [Recommended by the code search plan]" : ""}${L[a].x != null ? ` at x=${L[a].x}` : L[a].x_after != null ? `, ending at x=${L[a].x_after}` : ""}.`]));
    const compact = { goal: state.objective, player: state.player, press: { state: state.press.state }, trap: { state: state.trap.state } };
    const body = { state: compact, model: "latest", questions: { next_action: { type: "choice",
      instructions: "Choose the next controller action. Each option shows the result predicted by code. Never choose a result that means death. Prefer results that move right toward the far ground and the goal.", criteria: crit } } };
    const t0 = performance.now();
    const r = await (await fetch(MODEL_URL, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) })).json();
    const ms = performance.now() - t0;
    const A = r.answers?.values || r.answers || {}; const c = A.next_action, probs = c.probabilities || {};
    const a = ACTS.includes(c.choice) ? c.choice : Object.keys(probs).sort((x, y) => probs[y] - probs[x])[0];
    return { a, probs, noul: null, score: null, ms };
  }
  const rules = POLICY === "systemone";
  const body = { state, model: "latest", questions: {
    next_action: { type: "choice", instructions: rules ? INSTR_RULES : INSTR_FACTS, criteria: rules ? DESC : DESC_FACTS },
    jump_needed: { type: "noul", instructions: rules
      ? "Do `landing` predictions indicate that a forward jump should begin or remain held now? `landing.takeoff_window_closes_this_decision=true` is unambiguously yes. Also count `landing.if_chosen_now.right_jump.surface` of `platform` or `far_ground` as yes."
      : "Should a forward jump begin or remain held now?" },
    danger: { type: "score", instructions: "How dangerous is the character's immediate situation?", criteria: ["Safe open movement", "Pit or trap soon", "Immediate fall or spike contact"] } } };
  const t0 = performance.now();
  const r = await (await fetch(MODEL_URL, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) })).json();
  const ms = performance.now() - t0;
  const A = r.answers?.values || r.answers || {};
  const c = A.next_action, probs = c.probabilities || {};
  const a = ACTS.includes(c.choice) ? c.choice : Object.keys(probs).sort((x, y) => probs[y] - probs[x])[0];
  return { a, probs, noul: A.jump_needed?.noul ?? null, score: A.danger?.score ?? null, ms };
}

// ---------- 実行 ----------
const g = new Owata({}); await g.open(); await g.load();
if (!(await g.toGameplay()).ok) throw new Error("nav failed");
await g.resetAndFreeze();
const startOk = (r) => r.player && Math.abs(r.player.x - 99) <= 6 && Math.abs(r.player.y - 302) <= 6;
const down = new Set();
const setKeys = async (want) => { for (const k of [...down]) if (!want.has(k)) { await g.page.keyboard.up(k); down.delete(k); } for (const k of want) if (!down.has(k)) { await g.page.keyboard.down(k); down.add(k); } };
for (let ep = 0; ep < EPISODES; ep++) {
  await eyeReset();
  let r = await eye(await g.shot());
  if (!startOk(r)) { await g.load(); if (!(await g.toGameplay()).ok) throw new Error("nav failed"); await g.resetAndFreeze(); await eyeReset(); r = await eye(await g.shot()); }
  const T = makeTracker(); const decisions = [], frames = []; const recDir = OUT + `rec/ep${ep}/`; if (REC) fs.mkdirSync(recDir, { recursive: true });
  let held = "noop", pending = null, lastReq = -DECISION_FRAMES, lag = 0, decisionUpdated = false, outcome = "timeout", maxX = -1e9;
  let prevInfo = { action: "noop", frames_held: 0, progress_gained_px: 0, outcome: "none" }, heldSince = 0, xAtHold = null, crossed = false, platform = false, lastO = null;
  for (let frame = 0; frame < MAX_FRAMES; frame++) {
    const te = performance.now(); const buf = await g.shot(); r = await eye(buf); const eyeMs = performance.now() - te;
    if (REC) fs.writeFileSync(recDir + `${String(frame).padStart(5, "0")}.png`, buf);
    const o = track(T, r);
    if (!o) {
      if (!r.retry && T.lastX != null && T.lastX >= 600) { outcome = "right_edge"; break; }   // 画面の右端で自機が半分はみ出した(死亡ではない)
      if (T.missing >= 5 || r.retry) { outcome = "died"; break; }
    }
    else {
      if (lastO && Math.abs(o.x - lastO.x) > 40) { outcome = "lost"; break; }
      lastO = o; maxX = Math.max(maxX, o.x);
      if (o.surf === "platform") platform = true;
      if (o.surf === "far") crossed = true;
      if (o.x >= GOAL_X && o.grounded) { outcome = "goal"; break; }
    }
    frames.push({ f: frame, x: o?.x ?? null, dy: o?.dy ?? null, surf: o?.surf ?? null, held });
    if (pending && frame >= pending.readyAt) { prevInfo = { action: held, frames_held: frame - heldSince, progress_gained_px: xAtHold != null && o ? o.x - xAtHold : 0, outcome: o ? (o.surf ? "on_" + o.surf : "airborne") : "lost_sight" };
      held = pending.a; heldSince = frame; xAtHold = o?.x ?? null; decisionUpdated = true; pending = null; }
    if (o && !pending && frame - lastReq >= DECISION_FRAMES) {
      const tb = performance.now(); const { json } = buildState(o, T, lag, held, prevInfo, frame); const buildMs = performance.now() - tb;   // 予測と探索の時間
      const d = await decide(json);
      // EXTRA_MS: モデルなしの対照に、比べるモデルの応答時間(実測の中央値)を足して遅れをそろえる。記録の modelMs には入れない
      const L = Math.round((eyeMs + buildMs + d.ms + Number(process.env.EXTRA_MS || 0)) / FRAME_MS);
      decisions.push({ frame, a: d.a, probs: d.probs, noul: d.noul, score: d.score, criteria: d.criteria, modelMs: Math.round(d.ms), eyeMs: Math.round(eyeMs), buildMs: Math.round(buildMs), lagFrames: L, state: json });
      lag = L; lastReq = frame; pending = { a: d.a, readyAt: frame + L };
      if (L === 0) { held = d.a; heldSince = frame; xAtHold = o.x; decisionUpdated = true; pending = null; }
    }
    const want = new Set(KEYS[held]);
    if (decisionUpdated && isJump(held) && o?.grounded) want.delete("z");   // 押し直し
    decisionUpdated = false;
    await setKeys(want); await g.step(1);
  }
  if (outcome === "right_edge" && Number(process.env.EXPLORE_EDGE || 0) > 0) {   // 調査用: 右端の先を見るため、右を押し続けて録画
    await setKeys(new Set(["ArrowRight"]));
    for (let k = 0; k < Number(process.env.EXPLORE_EDGE); k++) { await g.step(1); if (REC) fs.writeFileSync(recDir + `edge${String(k).padStart(3, "0")}.png`, await g.shot()); }
  }
  await setKeys(new Set());
  if (REC) for (let k = 0; k < 40; k++) { await g.step(1); fs.writeFileSync(recDir + `end${String(k).padStart(2, "0")}.png`, await g.shot()); }
  const ms = decisions.map(d => d.modelMs).sort((a, b) => a - b);
  const rec = { ep, outcome, crossed, platform, maxX, frames: frames.length, decisions: decisions.length, deathAt: outcome === "died" && lastO ? { x: lastO.x, dy: lastO.dy } : null, decisionsLog: decisions, framesLog: frames };
  fs.appendFileSync(OUT + "episodes.jsonl", JSON.stringify(rec) + "\n");
  console.log(`[${TAG}] ep${ep}: ${outcome} frames=${frames.length} maxX=${maxX} platform=${platform} crossed=${crossed} decisions=${decisions.length} model p50=${ms[Math.floor(ms.length / 2)] ?? 0}ms`);
  await g.act(["r"], 2); await g.step(60);
}
await g.close();
