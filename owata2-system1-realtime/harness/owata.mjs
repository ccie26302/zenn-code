// 人生ｵﾜﾀの大冒険2 を Playwright で決定的に操作するための部品。
// 方針(設計書 v1 §2):
// - 公式ページ上で動かす(SWF を保存・改変しない)。広告・計測は遮断。
// - ブラウザの HTTP キャッシュは使い回す(作者サーバへの負荷を抑える)。試行ごとに保存領域だけ消して再読み込み。
// - メニューは実時間で、画面状態を画像で判定しながら進む。本編に入ったら時計を止めてコマ送り。
// - 乱数(Math.random / crypto.getRandomValues)は固定種で置き換える(設定で外せる)。
import { chromium } from "playwright";
import { PNG } from "pngjs";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export const URL_GAME = "https://king-soukutu.com/flash/owata2.html";
export const FRAME_MS = 1000 / 60;
const BLOCK = /(googlesyndication|google-analytics|googletagmanager|doubleclick|adservice|fc2\.com|jakou\.com|adsbygoogle|googleads|apis\.google\.com)/i;
// 音声の時計(AudioContext.currentTime)は実時間で進むので、偽の時計(performance.now)に連動させる
export const AUDIO_CLOCK_INIT = `(() => { const t0 = performance.now();
  for (const C of [window.BaseAudioContext, window.AudioContext, window.webkitAudioContext].filter(Boolean)) {
    try { Object.defineProperty(C.prototype, "currentTime", { configurable: true, get() { return (performance.now() - t0) / 1000; } }); } catch (e) {}
  }
  window.__audioClockPatched = true; })();`;
const seededInit = (seed) => `(() => { let s = ${seed >>> 0} || 1; const next = () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s; };
  Math.random = () => next() / 4294967296;
  crypto.getRandomValues = (arr) => { const u8 = new Uint8Array(arr.buffer, arr.byteOffset, arr.byteLength); for (let i = 0; i < u8.length; i++) u8[i] = next() & 255; return arr; }; })();`;

// 画面状態の判定(data/m0 の実画面で閾値を決めた: title orange≈1.65% / opening dark≈11% / game dark≈0.6%)
export function classify(pngBuf) {
  const p = PNG.sync.read(pngBuf); let orange = 0, dark = 0, red = 0, gray = 0; const n = p.width * p.height;
  for (let i = 0; i < p.data.length; i += 4) {
    const r = p.data[i], g = p.data[i + 1], b = p.data[i + 2];
    if (r > 200 && g > 80 && g < 180 && b < 90) orange++;
    if (r > 180 && g < 60 && b < 60) red++;          // ゲーム自身の読み込み画面の赤いバー
    if (r + g + b < 200) dark++;
    if (r + g + b < 600) gray++;                      // フェード中の灰色も含む「白でない」画素
  }
  const o = orange / n, d = dark / n, rd = red / n, gr = gray / n;
  const state = rd > 0.005 ? "loading" : o > 0.005 ? "title" : (d > 0.05 || gr > 0.08) ? "opening"
              : d < 0.03 && d > 0.002 ? "game" : "unknown";
  return { state, orange: o, dark: d, red: rd, gray: gr };
}

export function diffPixels(a, b) {
  const A = PNG.sync.read(a), B = PNG.sync.read(b); let n = 0;
  for (let i = 0; i < A.data.length; i += 4)
    if (Math.abs(A.data[i] - B.data[i]) + Math.abs(A.data[i + 1] - B.data[i + 1]) + Math.abs(A.data[i + 2] - B.data[i + 2]) > 30) n++;
  return n;
}

export class Owata {
  constructor({ headless = true, seedRng = 123456789, audioClock = false, noAudio = false, blockBgm = false, log = () => {} } = {}) {
    this.headless = headless; this.seedRng = seedRng; this.audioClock = audioClock; this.log = log;
    this.noAudio = noAudio; this.blockBgm = blockBgm;
    this.stats = { loads: 0, bytes: 0, blocked: 0 };
  }
  async open() {
    this.userDir = fs.mkdtempSync(path.join(os.tmpdir(), "owata-"));
    this.ctx = await chromium.launchPersistentContext(this.userDir, { headless: this.headless, viewport: { width: 1000, height: 700 } });
    if (this.seedRng) await this.ctx.addInitScript(seededInit(this.seedRng));
    if (this.audioClock) await this.ctx.addInitScript(AUDIO_CLOCK_INIT);
    // 音声を無効化(Ruffle は音声なしで動く)。BGM に合わせてコマを進める同期を切るため
    if (this.noAudio) await this.ctx.addInitScript(`(() => { window.AudioContext = undefined; window.webkitAudioContext = undefined; })();`);
    this.page = this.ctx.pages()[0] || await this.ctx.newPage();
    await this.page.route("**/*", (q) => {
      const u = q.request().url();
      if (BLOCK.test(u) || (this.blockBgm && /owata2_bgm\.swf/.test(u))) { this.stats.blocked++; return q.abort(); }
      return q.continue();
    });
    this.page.on("response", async (res) => {
      if (res.fromServiceWorker()) return;
      const len = Number(res.headers()["content-length"] || 0); this.stats.bytes += len;
    });
    // 時計は load() ごとに入れ直して最初から止める(読み込み〜本編まで全部コマ単位で決める)
  }
  async load() {
    // 保存領域を消してから読み込む(進行保存の持ち越し防止)。HTTP キャッシュは残る
    // ページを離れる瞬間に Ruffle が保存(SharedObject→localStorage)を書き戻すので、
    // いったん about:blank に移ってから CDP でサイトの保存領域を消す。HTTP キャッシュは残す。
    await this.page.goto("about:blank");
    const cdp = await this.ctx.newCDPSession(this.page);
    await cdp.send("Storage.clearDataForOrigin", { origin: "https://king-soukutu.com",
      storageTypes: "local_storage,indexeddb,websql,service_workers,cache_storage,shader_cache" });
    await cdp.detach();
    await this.page.clock.install({ time: new Date("2026-10-02T00:00:00Z") });
    await this.page.clock.pauseAt(new Date("2026-10-02T00:00:00.100Z"));
    await this.page.goto(URL_GAME, { waitUntil: "domcontentloaded" });
    this.stats.loads++;
    await this.page.waitForFunction(() => { const p = document.querySelector("ruffle-embed"); return p && p.readyState === 2; }, null, { timeout: 60000 });
    // 通信(本体 SWF・BGM SWF・wasm)と Ruffle の展開を実時間で済ませておく。ゲーム時間は進めない
    await this.page.waitForLoadState("networkidle").catch(() => {});
    await this.page.waitForTimeout(3000);
    this.el = await this.page.$("ruffle-embed");
    this.box = await this.el.boundingBox();
    try { await this.cdp?.detach(); } catch (e) {} this.cdp = null;
    this.ruffleVersion = await this.page.evaluate(() => window.RufflePlayer && window.RufflePlayer.version);
    const saves = await this.page.evaluate(() => Object.keys(localStorage));
    return { ruffleVersion: this.ruffleVersion, localStorageKeys: saves };
  }
  G(x, y) { return [this.box.x + x * this.box.width / 640, this.box.y + y * this.box.height / 360]; }
  // 撮影: CDP で範囲指定(要素スクリーンショットの約半分の時間。判定結果は同一を確認済み)
  async shot() {
    if (!this.cdp) { this.cdp = await this.ctx.newCDPSession(this.page); }
    const b = this.box;
    const r = await this.cdp.send("Page.captureScreenshot", { format: "png", optimizeForSpeed: true, clip: { x: b.x, y: b.y, width: b.width, height: b.height, scale: 1 } });
    return Buffer.from(r.data, "base64");
  }
  async state() { const b = await this.shot(); return { ...classify(b), buf: b }; }
  // 時計を止めたまま、画面状態を判定しながら本編まで進む(全部コマ単位=決定的)
  // 読み込み中だけは実時間で待つ(通信が要る)が、ゲーム時間は「読み込み画面が終わるまで10コマずつ」進めるだけ
  async clickSpaced(x, y) {
    await this.page.mouse.move(...this.G(x, y)); await this.step(5);
    await this.page.mouse.down(); await this.step(5); await this.page.mouse.up(); await this.step(5);
  }
  async hold(key, frames = 4) { await this.page.keyboard.down(key); await this.step(frames); await this.page.keyboard.up(key); await this.step(2); }
  async toGameplay({ maxIters = 120 } = {}) {
    const trace = []; let loadingIters = 0, gameStreak = 0;
    for (let i = 0; i < maxIters + loadingIters; i++) {
      const s = await this.state(); trace.push(s.state);
      // 読み込み中はコマを進めるだけ(実時間は待たない)。通信は load() で先に終わらせてある → 進めるコマ数が毎回同じになる
      if (s.state === "loading") { loadingIters++; if (loadingIters > 600) break; await this.step(10); continue; }
      if (s.state === "game") { if (++gameStreak >= 3) return { ok: true, trace, loadingIters }; await this.step(20); continue; }
      gameStreak = 0;
      if (s.state === "title") { await this.clickSpaced(330, 218); await this.step(60); }
      else if (s.state === "opening") { await this.hold("s"); await this.step(60); }
      else await this.step(20);
    }
    return { ok: false, trace, loadingIters };
  }
  // 本編でステージを最初からにして、時計を止める
  async resetAndFreeze({ settleFrames = 90, mode = "freeze_then_r", settleMs = 1500 } = {}) {
    if (mode === "r_then_freeze") {          // 旧方式: 実時間で R → 待つ → 止める(動く足場の位相がずれる)
      await this.page.keyboard.press("r"); await this.page.waitForTimeout(settleMs);
      const now = await this.page.evaluate(() => Date.now());
      await this.page.clock.pauseAt(now + 20);
    } else {                                  // 新方式: 時計は止まっている → R をコマ上で押す → 決まったコマ数だけ進める
      await this.act(["r"], 2);
      await this.step(settleFrames);
    }
    await this.hidePlayButton();
  }
  async hidePlayButton() {
    await this.page.evaluate(() => { const r = document.querySelector("ruffle-embed")?.shadowRoot; const e = r && r.getElementById("play-button"); if (e) e.style.display = "none"; });
  }
  // rec が配列なら、進めたコマを1枚ずつ撮っておく(試走中の録画用。時計は止まっているのでゲームの進みには影響しない)
  async step(frames = 1) { for (let f = 0; f < frames; f++) { await this.page.clock.runFor(FRAME_MS); if (this.rec) this.rec.push({ buf: await this.shot(), ...this.recLabel }); } }
  // キーを押したまま frames だけ進めて離す(離したことを 1 フレームで反映)
  async act(keys, frames) {
    for (const k of keys) await this.page.keyboard.down(k);
    await this.step(frames);
    for (const k of keys) await this.page.keyboard.up(k);
    await this.step(1);
  }
  // 行動(ACTIONS2 の形)を実行: キーごとに決まったコマ数だけ押して離す
  async actSpec(spec) {
    const ks = Object.entries(spec.keys);
    for (const [k] of ks) await this.page.keyboard.down(k);
    for (let f = 1; f <= spec.total; f++) {
      await this.step(1);
      for (const [k, n] of ks) if (n === f) await this.page.keyboard.up(k);
    }
    for (const [k, n] of ks) if (n > spec.total) await this.page.keyboard.up(k);
    await this.step(1);
  }
  async close() { await this.ctx?.close(); try { fs.rmSync(this.userDir, { recursive: true, force: true }); } catch (e) {} }
}

// 修正 B4: 操作どおりの11択。keys = {キー: 押すコマ数}, total = この行動にかける総コマ数
export const ACTIONS2 = {
  right: { keys: { ArrowRight: 6 }, total: 6 }, left: { keys: { ArrowLeft: 6 }, total: 6 }, wait: { keys: {}, total: 6 },
  jump_small: { keys: { z: 2 }, total: 6 }, rightjump_small: { keys: { z: 2, ArrowRight: 6 }, total: 6 }, leftjump_small: { keys: { z: 2, ArrowLeft: 6 }, total: 6 },
  jump_big: { keys: { z: 16 }, total: 16 }, rightjump_big: { keys: { z: 16, ArrowRight: 16 }, total: 16 }, leftjump_big: { keys: { z: 16, ArrowLeft: 16 }, total: 16 },
  attack: { keys: { x: 2 }, total: 6 }, pose: { keys: { s: 3 }, total: 6 },
};

export const ACTIONS = {
  right: ["ArrowRight"], left: ["ArrowLeft"], jump: ["z"], rightjump: ["ArrowRight", "z"],
  leftjump: ["ArrowLeft", "z"], shoot: ["x"], wait: [],
};
