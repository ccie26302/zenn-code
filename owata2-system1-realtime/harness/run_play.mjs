// プレイ実行器(同期運転)。ハーネスは「目・記憶・実行」だけ。判断は頭(POLICY)に任せる(修正 B1)。
//   POLICY=random      … 乱択(R1)
//   POLICY=systemone   … System-1(MODEL_URL の /v1/systemone、Choice の確率が高い順に試す)(S1/SR1)
// 記憶: 死ぬ直前の位置キー(ワールド x/16, y/24, 接地/空中)で取った行動を禁止。全行動が禁止なら1手前へ遡る(K=1)。
// 指標: 穴を越えた(ワールド x が GOAL_X を超えた)までの死亡回数・エピソード数・判断回数。
import { Owata, ACTIONS, ACTIONS2 } from "./owata.mjs";
import fs from "node:fs";

const POLICY = process.env.POLICY || "random", MODEL_URL = process.env.MODEL_URL || "", LANG = process.env.LANG_ || "ja";
const TAG = process.env.TAG || POLICY;
const EPISODES = Number(process.env.EP || 30), MAX_STEPS = Number(process.env.STEPS || 80), HOLD = Number(process.env.HOLD || 6);
const GOAL_X = Number(process.env.GOAL_X || 420), SEED = Number(process.env.SEED || 7);
const REALTIME = process.env.REALTIME !== "0";   // 修正 B3: 既定はリアルタイム相当(判断にかかった時間ぶんゲームを進める)
const LAG_MODE = process.env.LAG_MODE || "full";  // full = 目＋モデル / model = モデルの判断時間だけ(目は一瞬とみなす)
const FRAME_MS = 1000 / 60;
const EYE = process.env.EYE || "http://127.0.0.1:8099";
const OUT = new URL(`../data/play/${TAG}/`, import.meta.url).pathname; fs.mkdirSync(OUT, { recursive: true });
// 修正 B4: 操作どおりの11択(説明は操作の効果だけ。いつ使えとは書かない)
const ACTSET = process.env.ACTSET || "v2";
// 修正 B6(ユーザー指定): v3 = 大ジャンプを標準の「ジャンプ」と呼び、ジャンプの先頭に置く。小ジャンプは補助。押すキーとコマ数は v2 と同じ
const ACTS = ACTSET === "v1" ? ["right", "rightjump", "jump", "wait", "left", "leftjump"]
  : ACTSET === "v3" ? ["right", "left", "wait", "jump_big", "rightjump_big", "leftjump_big", "jump_small", "rightjump_small", "leftjump_small", "attack", "pose"]
  : Object.keys(ACTIONS2);
const LABEL = ACTSET === "v1" ? {
  ja: { right: "右へ歩く", rightjump: "右へ跳ぶ(右を押しながらジャンプ)", jump: "その場で跳ぶ", wait: "何もしない", left: "左へ歩く", leftjump: "左へ跳ぶ(左を押しながらジャンプ)" },
  en: { right: "walk right", rightjump: "jump to the right (hold right and jump)", jump: "jump in place", wait: "do nothing", left: "walk left", leftjump: "jump to the left (hold left and jump)" },
} : {
  ja: { right: "右へ歩く(空中でも右へ動く)", left: "左へ歩く(空中でも左へ動く)", wait: "何もしない",
        jump_small: "その場で小ジャンプ(低い)", rightjump_small: "右へ小ジャンプ(低い)", leftjump_small: "左へ小ジャンプ(低い)",
        jump_big: "その場で大ジャンプ(高い)", rightjump_big: "右へ大ジャンプ(高い)", leftjump_big: "左へ大ジャンプ(高い)",
        attack: "攻撃(前に弾を撃つ)", pose: "ポーズを取る" },
  en: { right: "walk right (also moves right in the air)", left: "walk left (also moves left in the air)", wait: "do nothing",
        jump_small: "small jump in place (low)", rightjump_small: "small jump to the right (low)", leftjump_small: "small jump to the left (low)",
        jump_big: "big jump in place (high)", rightjump_big: "big jump to the right (high)", leftjump_big: "big jump to the left (high)",
        attack: "attack (shoot a bullet forward)", pose: "strike a pose" },
};
if (ACTSET === "v3") {
  Object.assign(LABEL.ja, { jump_big: "その場でジャンプ", rightjump_big: "右へジャンプ", leftjump_big: "左へジャンプ",
    jump_small: "その場で小ジャンプ(ボタンを短く押す・低い)", rightjump_small: "右へ小ジャンプ(ボタンを短く押す・低い)", leftjump_small: "左へ小ジャンプ(ボタンを短く押す・低い)" });
  Object.assign(LABEL.en, { jump_big: "jump in place", rightjump_big: "jump to the right", leftjump_big: "jump to the left",
    jump_small: "small hop in place (tap the button, low)", rightjump_small: "small hop to the right (tap the button, low)", leftjump_small: "small hop to the left (tap the button, low)" });
}
// 修正 B5: 良い記憶(経験で優先)＋未試行ボーナス
const MEMORY = process.env.MEMORY || "ban";          // ban = 禁止だけ / gain = 禁止＋経験で優先
const BETA = Number(process.env.BETA || 1), GAMMA = Number(process.env.GAMMA || 0.5), H = 8;
// B5 調整(rt3 を見て): ALPHA=モデル確率の重み、STATKEY=coarse なら経験は足場を除いた粗い位置で数える、GAIN=net なら戻った分は減点
const REC = process.env.REC === "1";
// ユーザー指摘(2026-10-02): 危険を潜り抜けるゲームで「死んだ行動を禁止」すると何もできなくなる → NOBAN=1 で禁止しない
const NOBAN = process.env.NOBAN === "1";
// 軽い罰(2026-10-02): 禁止の代わりに、死ぬ直前の3手の経験の点を下げる(直前ほど重い。行動は消さない)
const SOFTPEN = Number(process.env.SOFTPEN || 0);
const ALPHA = Number(process.env.ALPHA || 1), STATKEY = process.env.STATKEY || "fine", GAINMODE = process.env.GAIN || "max";
const sk = (k) => STATKEY === "coarse" ? k.split(",").slice(0, 3).join(",") : k;
const stat = new Map();                               // `${key}|${action}` -> {n, gainSum, gainN}
const st = (k, a) => { const id = `${sk(k)}|${a}`; if (!stat.has(id)) stat.set(id, { n: 0, gainSum: 0, gainN: 0 }); return stat.get(id); };
function memScore(k, a, p) {
  const s = st(k, a); const Nk = ACTS.reduce((t, x) => t + st(k, x).n, 0);
  const gain = s.gainN ? s.gainSum / s.gainN : 0;
  const bonus = GAMMA * Math.sqrt(Math.log(Nk + 1) / (s.n + 1));
  return { score: ALPHA * Math.log((p ?? 0) + 1e-3) + BETA * gain / 50 + bonus, gain, bonus, n: s.n };
}
const onPlatform = (t) => t.k.includes(",g,") && t.x >= 200 && t.x <= 380 && t.y >= 215 && t.y <= 250;
const doAct = (g, a) => ACTSET === "v1" ? g.act(ACTIONS[a], HOLD) : g.actSpec(ACTIONS2[a]);
let s = SEED; const rnd = () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
const eye = async (buf) => (await fetch(EYE + "/perceive", { method: "POST", body: buf })).json();
const eyeReset = () => fetch(EYE + "/reset", { method: "POST" });
// 修正 B2: 見えている動くもの(足場の相対位置と向き)もキーに入れる
const keyOf = (r) => {
  const pl = r.platform && r.player ? `${Math.floor((r.platform.x0 - r.player.x) / 32)}${(r.platform.moving || "?")[0]}` : "none";
  return `${Math.floor(r.world.x / 16)},${Math.floor(r.world.y / 24)},${r.ground?.on_ground ? "g" : "a"},${pl}`;
};
const banned = new Map();
const isBanned = (k, a) => banned.get(k)?.has(a);
const ban = (k, a) => { if (!banned.has(k)) banned.set(k, new Set()); banned.get(k).add(a); };

// 状態の文章(見えているものだけ。どう動けばよいかのヒントは書かない)
// 修正 B7: 目にトゲの列を足す(STATE_V=2)。見えている事実(位置・自機との上下・前回からの動き)だけを書く
const STATE_V = process.env.STATE_V || "1";
function spikeText(r) {
  if (STATE_V !== "2") return "";
  const p = r.player, feet = p.box[3], sp = r.spikes || [];
  if (!sp.length) return LANG === "en" ? "\nNo spikes are visible." : "\nトゲは見えない。";
  return sp.map(s => {
    const tip = s.y - 11, d = feet - tip;   // 正 = トゲの先が足元より上
    const under = p.x >= s.x0 && p.x <= s.x1;
    const mv = s.dy == null ? "" : s.dy < -2 ? (LANG === "en" ? ` It moved up ${-s.dy}px since the last look.` : `前回より ${-s.dy}px 上がった。`)
      : s.dy > 2 ? (LANG === "en" ? ` It moved down ${s.dy}px since the last look.` : `前回より ${s.dy}px 下がった。`) : (LANG === "en" ? " It is not moving." : "動いていない。");
    return LANG === "en"
      ? `\nA row of spikes at x=${s.x0}-${s.x1}; the spike tips are ${Math.abs(d)}px ${d >= 0 ? "above" : "below"} your feet${under ? ", directly under/around you" : ""}.${mv}`
      : `\nトゲの列が x=${s.x0}〜${s.x1} にある。トゲの先は自機の足元より ${Math.abs(d)}px ${d >= 0 ? "上" : "下"}${under ? "(自機の真下の範囲)" : ""}。${mv}`;
  }).join("");
}
// STATE_V=4(2026-10-02、外部レビュー対応): 3 と同じ内容で、足場の向きが「止まっている」ときの誤った文
// 「(止まって動いている)」「moving still」を直し、英語でも目的と向こう岸を書く。3 以前の試走の文は変えない。
function stateText(r) {
  const p = r.player, gr = r.ground, pl = r.platform;
  const v34 = STATE_V === "3" || STATE_V === "4", fix = STATE_V === "4";
  if (LANG === "en") {
    const g = !gr ? "" : gr.on_ground
      ? `The ground under you ${gr.edge_right_px == null ? "continues to the right as far as visible" : `ends ${gr.edge_right_px}px to the right${gr.spikes_after_right_edge ? ", with spikes beyond it" : ""}`}.`
        + (fix && gr.far_ground_px != null ? ` Beyond that, the ground continues again ${gr.far_ground_px}px to the right.` : "")
      : "You are in the air.";
    const mvEn = (m) => fix ? ({ left: ", moving left", right: ", moving right", still: ", not moving" }[m] || "") : `, moving ${m}`;
    const f = pl ? `A floating platform is at x=${pl.x0}-${pl.x1}, y=${pl.y0}${pl.moving ? mvEn(pl.moving) : ""}.` : "No floating platform is visible.";
    const goal = fix ? "Goal: reach the right edge of the screen and go on to the next stage." : "Goal: move right and do not die.";
    return `Side-scrolling action game. You control the character. ${goal}\nYou: x=${p.x}, y=${p.y} (smaller y is higher). ${g}\n${f}${spikeText(r)}`;
  }
  const g = !gr ? "" : gr.on_ground
    ? `足元の地面は${gr.edge_right_px == null ? "見える範囲では右に途切れない" : `右へ ${gr.edge_right_px}px で途切れる${gr.spikes_after_right_edge ? "(その先にトゲがある)" : ""}`}。`
      + (v34 && gr.far_ground_px != null ? `その先、右へ ${gr.far_ground_px}px の所から地面がまた続いている。` : "")
    : "空中にいる。";
  const mvJa = (m) => fix ? ({ left: "(左へ動いている)", right: "(右へ動いている)", still: "(止まっている)" }[m] || "") : `(${{ left: "左へ", right: "右へ", still: "止まって" }[m]}動いている)`;
  const f = pl ? `宙に浮いた足場が x=${pl.x0}〜${pl.x1}、y=${pl.y0} にある${pl.moving ? mvJa(pl.moving) : ""}。` : "宙に浮いた足場は見えない。";
  return `横スクロールのアクションゲーム。あなたは自機を操作する。${v34 ? "目的: 画面の右端まで進んで、次のステージへ行くこと。" : "目的: 右へ進むこと、死なないこと。"}\n自機: x=${p.x}, y=${p.y}(y が小さいほど上)。${g}\n${f}${spikeText(r)}`;
}

async function decide(r, allowed) {
  if (POLICY === "random") return { a: allowed[Math.floor(rnd() * allowed.length)], probs: null };
  const keys = "ABCDEFGHIJKL".split(""); const crit = {}; const map = {};
  allowed.forEach((a, i) => { crit[keys[i]] = LABEL[LANG][a]; map[keys[i]] = a; });
  if (allowed.length === 1) return { a: allowed[0], probs: null };
  const body = { state: stateText(r), model: "latest",
    questions: { move: { type: "choice", instructions: LANG === "en" ? "Choose the next action (about 0.1 s)." : "次の操作(約0.1秒)を1つ選ぶ。", criteria: crit } } };
  const t0 = performance.now();
  const resp = await (await fetch(MODEL_URL, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) })).json();
  const node = resp.answers?.values?.move || resp.answers?.move || resp.move;
  const probs = node.probabilities || {};
  if (MEMORY === "gain") {
    const sc = Object.entries(map).map(([key, a]) => ({ a, key, ...memScore(r.__k, a, probs[key]) }));
    sc.sort((x, y) => y.score - x.score);
    return { a: sc[0].a, probs, ms: performance.now() - t0, mem: Object.fromEntries(sc.map(x => [x.a, { s: +x.score.toFixed(2), g: +x.gain.toFixed(1), b: +x.bonus.toFixed(2) }])) };
  }
  // 確率の高い順(記憶で禁止された行動は既に選択肢から外してある)
  const best = Object.keys(map).sort((x, y) => (probs[y] ?? 0) - (probs[x] ?? 0))[0];
  return { a: map[node.choice] && probs[node.choice] >= (probs[best] ?? 0) ? map[node.choice] : map[best], probs, ms: performance.now() - t0 };
}

const g = new Owata({});
await g.open(); await g.load();
if (!(await g.toGameplay()).ok) throw new Error("nav failed");
await g.resetAndFreeze();
const startOk = (r) => r.player && Math.abs(r.player.x - 99) <= 6 && Math.abs(r.player.y - 302) <= 6;
const log = [], log_ban = []; let deaths = 0, decisions = 0, solvedAt = null, bestX = -1e9;
for (let ep = 0; ep < EPISODES; ep++) {
  await eyeReset();
  const te0 = performance.now();
  let r = await eye(await g.shot());
  if (!startOk(r)) {   // 樹海のチェックポイント等でスタート地点にいない → 読み直す
    await g.load(); if (!(await g.toGameplay()).ok) throw new Error("nav failed"); await g.resetAndFreeze();
    await eyeReset(); r = await eye(await g.shot());
    if (!startOk(r)) { console.log("start check failed"); }
  }
  // REC=1: 試走そのものを全コマ録画(再生し直すと1コマのずれで結果が変わる場面があるため)
  if (REC) { g.rec = []; g.recLabel = { step: 0, action: "start" }; for (let i = 0; i < 20; i++) g.rec.push({ buf: await g.shot(), step: 0, action: "start" }); }
  const traj = []; let lost = false, goal = false, crossed = false, missing = 0, died = false, maxX = r.world ? r.world.x : -1e9, steps;
  // この状態 r を作るのにかかった目の時間(撮影＋目のサーバ)。最初の1回も実測する(同じコマなのでカメラ追跡には影響しない)
  let eyeMs; { const t = performance.now(); r = await eye(await g.shot()); eyeMs = performance.now() - t; }
  for (steps = 0; steps < MAX_STEPS; steps++) {
    if (!r.player) break;
    const k = keyOf(r);
    const allowed = ACTS.filter(a => !isBanned(k, a));
    if (!allowed.length) break;
    const td = performance.now();
    r.__k = k;
    const d = await decide(r, allowed); decisions++;
    const modelMs = performance.now() - td;
    // リアルタイム相当: 撮影の瞬間から判断が出るまでの時間ぶん、手放し状態でゲームを進める
    const lagFrames = REALTIME ? Math.round(((LAG_MODE === "model" ? 0 : eyeMs) + modelMs) / FRAME_MS) : 0;
    if (g.rec) g.recLabel = { step: steps + 1, action: "thinking", next: d.a, lag: lagFrames };
    if (lagFrames > 0) await g.step(lagFrames);
    if (g.rec) g.recLabel = { step: steps + 1, action: d.a };
    await doAct(g, d.a);
    const te = performance.now();
    const prev = r; r = await eye(await g.shot());
    eyeMs = performance.now() - te;
    traj.push({ k, a: d.a, x: prev.world.x, y: prev.world.y, st: STATE_V !== "1" ? stateText(prev) : undefined, probs: d.probs, mem: d.mem, ms: d.ms, modelMs: Math.round(modelMs), eyeMs: Math.round(eyeMs), lagFrames });
    // 見張り(2026-10-02): 判断の間に 100px 以上飛んだら追跡を見失った(樹海の縦スクロール等)。その回はここで打ち切り、以後を記憶に入れない
    if (r.player && !r.retry && Math.abs(r.world.x - prev.world.x) > 100) { lost = true; break; }
    // ゴール: 位置の数字に加えて、画面上で「地面に立ち、トゲの列より右にいる」ことも条件にする
    if (r.player && !r.retry) { missing = 0; maxX = Math.max(maxX, r.world.x); if (r.ground?.on_ground && r.world.x >= 385 && (r.spikes || []).some(q => r.player.x > q.x1 + 5)) crossed = true;
      if (r.world.x > GOAL_X && r.ground?.on_ground) { goal = true; break; } }
    else if (++missing >= 2 || r.retry) { died = true; break; }
    else r = prev;   // 1コマだけ見失った: 直前の状態で続ける
  }
  if (MEMORY === "gain") {
    // 各判断の後 H 手で到達 x がどれだけ伸びたか(死ぬ直前の数手は禁止で扱うので対象外)。足場に乗れたら +100
    const lastSafe = died && !NOBAN ? traj.length - 3 : traj.length;
    for (let i = 0; i < traj.length; i++) {
      const s = st(traj[i].k, traj[i].a); s.n++;
      if (i >= lastSafe) continue;
      const fut = traj.slice(i + 1, i + 1 + H);
      let gain = GAINMODE === "net" ? (fut.length ? fut.at(-1).x : traj[i].x) - traj[i].x : Math.max(0, ...fut.map(t => t.x)) - traj[i].x;
      if (fut.some(onPlatform)) gain += 100;
      s.gainSum += GAINMODE === "net" ? gain : Math.max(gain, 0); s.gainN++;
    }
  }
  if (died && SOFTPEN && MEMORY === "gain") {
    for (let d = 0; d < 3 && d < traj.length; d++) { const t = traj[traj.length - 1 - d]; st(t.k, t.a).gainSum -= SOFTPEN * 0.5 ** d; }
  }
  if (died && NOBAN) deaths++;
  else if (died) {
    deaths++;
    // 修正 B2: 最後に地面にいたときの判断を禁止(空中の操作は対象外)。全部禁止なら、その前の地面の判断へ遡る
    const groundIdx = traj.map((t, i) => t.k.includes(",g,") ? i : -1).filter(i => i >= 0);
    const order = groundIdx.length ? groundIdx.reverse() : [traj.length - 1];
    let bannedAt = null;
    for (const i of order) { const t = traj[i]; ban(t.k, t.a); bannedAt = { i, k: t.k, a: t.a }; if (ACTS.some(a => !isBanned(t.k, a))) break; }
    log_ban.push({ ep, ...bannedAt, depth: traj.length - 1 - (bannedAt?.i ?? 0) });
  }
  bestX = Math.max(bestX, maxX);
  const solved = goal;
  if (solved && solvedAt == null) solvedAt = { ep, deaths, decisions };
  const last = traj[traj.length - 1];
  log.push({ ep, steps, died, lost, crossed, maxX, solved, onPlatform: traj.some(onPlatform), deathAt: died && last ? { x: last.x, y: last.y } : null, banned: banned.size, traj });
  fs.appendFileSync(OUT + "episodes.jsonl", JSON.stringify(log[log.length - 1]) + "\n");
  const rjb = traj.filter(t => t.a === "rightjump_big").length;
  console.log(`[${TAG}] ep${ep}: steps=${steps} died=${died} maxX=${maxX} best=${bestX} 死亡累計=${deaths} 禁止キー=${banned.size} 右大ジャンプ=${rjb}${traj.some(onPlatform) ? " ◆足場に乗った" : ""}${crossed ? " ★向こう岸に着いた" : ""}${solved ? " ★★次へ" : ""}${lost ? " (追跡を見失い打ち切り)" : ""}`);
  if (REC) {
    g.recLabel = { step: steps, action: "end" }; await g.step(40);
    if (process.env.REC_ALL === "1" || ep % 10 === 0 || maxX > 185 || traj.some(onPlatform) || solved || ep === EPISODES - 1) {
      const dir = OUT + `rec/ep${ep}/`; fs.mkdirSync(dir, { recursive: true });
      const head = { tag: TAG, ep, policy: POLICY, died, maxX, steps: traj.length, banned: banned.size };
      g.rec.forEach((f, i) => fs.writeFileSync(dir + `${String(i).padStart(5, "0")}.png`, f.buf));
      fs.writeFileSync(dir + "meta.json", JSON.stringify(g.rec.map((f, i) => ({ i, ...head, step: f.step, action: f.action, next: f.next, lag: f.lag, probs: null }))));
    }
    g.rec = null;
  }
  if (solved) break;
  await g.act(["r"], 2); await g.step(60);
}
fs.writeFileSync(OUT + "log.json", JSON.stringify({ TAG, POLICY, MODEL_URL, LANG, HOLD, GOAL_X, SEED, REALTIME, LAG_MODE, ACTSET, MEMORY, BETA, GAMMA, ALPHA, STATKEY, GAINMODE, NOBAN, SOFTPEN, STATE_V, solvedAt, deaths, decisions, bestX,
  banned: [...banned].map(([k, v]) => [k, [...v]]), log_ban, log }, null, 1));
console.log(JSON.stringify({ TAG, solvedAt, deaths, decisions, bestX }));
await g.close();
