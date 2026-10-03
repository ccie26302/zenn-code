// 画面から「自機の有無・位置」と「R:Retry 表示(死亡の確定)」を取る簡易な目(ルール特徴, AI なし)。
// - 自機: 背景(自機のいない画面)との差分で、白でない画素の塊のうち 幅>=4・高さ>=6・面積>=15 のものを集める。
//         合計面積 >= AREA_MIN で「あり」。動く足場の端の筋(面積≈20)と分けるため。閾値は M1 で正解ラベルから決め直す。
// - R:Retry: 右上の領域(x>=520, y<=40)に白でない画素がまとまって出たら「表示あり」。
import { PNG } from "pngjs";

export const AREA_MIN = 45;

function readGray(buf) {
  const p = PNG.sync.read(buf); const g = new Uint16Array(p.width * p.height);
  for (let i = 0, j = 0; i < p.data.length; i += 4, j++) g[j] = p.data[i] + p.data[i + 1] + p.data[i + 2];
  return { w: p.width, h: p.height, g };
}

export function makeBackground(buf, dilate = 2) {
  const { w, h, g } = readGray(buf); const m = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (g[y * w + x] < 300)
    for (let dy = -dilate; dy <= dilate; dy++) for (let dx = -dilate; dx <= dilate; dx++) {
      const yy = y + dy, xx = x + dx; if (yy >= 0 && yy < h && xx >= 0 && xx < w) m[yy * w + xx] = 1;
    }
  return { w, h, m };
}

export function perceive(buf, bg) {
  const { w, h, g } = readGray(buf);
  // R:Retry 表示
  let retry = 0; for (let y = 0; y <= 40; y++) for (let x = 520; x < w; x++) if (g[y * w + x] < 300) retry++;
  // 前景の塊
  const fg = new Uint8Array(w * h);
  for (let i = 0; i < w * h; i++) if (g[i] < 300 && !bg.m[i]) fg[i] = 1;
  for (let y = 0; y <= 40; y++) for (let x = 520; x < w; x++) fg[y * w + x] = 0;   // R:Retry は除外
  const seen = new Uint8Array(w * h); const blobs = [];
  for (let i = 0; i < w * h; i++) {
    if (!fg[i] || seen[i]) continue;
    let minx = 1e9, maxx = -1, miny = 1e9, maxy = -1, area = 0; const st = [i]; seen[i] = 1;
    while (st.length) {
      const k = st.pop(); const x = k % w, y = (k / w) | 0; area++;
      if (x < minx) minx = x; if (x > maxx) maxx = x; if (y < miny) miny = y; if (y > maxy) maxy = y;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        const xx = x + dx, yy = y + dy; if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
        const kk = yy * w + xx; if (fg[kk] && !seen[kk]) { seen[kk] = 1; st.push(kk); }
      }
    }
    blobs.push({ area, w: maxx - minx + 1, h: maxy - miny + 1, cx: (minx + maxx) / 2, cy: (miny + maxy) / 2 });
  }
  const cand = blobs.filter(b => b.w >= 4 && b.h >= 6 && b.area >= 15);
  const area = cand.reduce((s, b) => s + b.area, 0);
  const player = area >= AREA_MIN
    ? { x: Math.round(cand.reduce((s, b) => s + b.cx * b.area, 0) / area), y: Math.round(cand.reduce((s, b) => s + b.cy * b.area, 0) / area), area }
    : null;
  return { player, retry: retry > 150, retryPixels: retry, nBlobs: blobs.length };
}

// ---- v2: 「背景より暗くなった画素」だけを取る(膨張マスクをやめた)。動く足場は形で除外 ----
// 自機が看板と重なっても、重なっていない部分は拾える。足場「[===]」は横長で薄い塊(幅>40・高さ<16)。
export function makeBackground2(buf) { return readGray(buf); }

export function perceive2(buf, bg, { areaMin = 30, mergeDist = 40 } = {}) {
  const { w, h, g } = readGray(buf);
  let retry = 0; for (let y = 0; y <= 40; y++) for (let x = 520; x < w; x++) if (g[y * w + x] < 300) retry++;
  const fg = new Uint8Array(w * h);
  for (let i = 0; i < w * h; i++) if (g[i] < 300 && bg.g[i] - g[i] > 150) fg[i] = 1;   // 背景より暗くなった
  for (let y = 0; y <= 40; y++) for (let x = 520; x < w; x++) fg[y * w + x] = 0;
  const seen = new Uint8Array(w * h); const blobs = [];
  for (let i = 0; i < w * h; i++) {
    if (!fg[i] || seen[i]) continue;
    let minx = 1e9, maxx = -1, miny = 1e9, maxy = -1, area = 0; const st = [i]; seen[i] = 1;
    while (st.length) {
      const k = st.pop(); const x = k % w, y = (k / w) | 0; area++;
      if (x < minx) minx = x; if (x > maxx) maxx = x; if (y < miny) miny = y; if (y > maxy) maxy = y;
      for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {     // 文字の隙間をまたいでつなぐ
        const xx = x + dx, yy = y + dy; if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
        const kk = yy * w + xx; if (fg[kk] && !seen[kk]) { seen[kk] = 1; st.push(kk); }
      }
    }
    blobs.push({ area, x0: minx, x1: maxx, y0: miny, y1: maxy, w: maxx - minx + 1, h: maxy - miny + 1 });
  }
  const platformLike = (b) => b.w > 40 && b.h < 16;
  const cand = blobs.filter(b => !platformLike(b) && b.area >= 8);
  if (!cand.length) return { player: null, retry: retry > 150, blobs: blobs.length };
  // 一番大きい塊の近くの塊をまとめて自機とする
  cand.sort((a, b) => b.area - a.area);
  const c0 = cand[0]; const cx0 = (c0.x0 + c0.x1) / 2, cy0 = (c0.y0 + c0.y1) / 2;
  const grp = cand.filter(b => Math.hypot((b.x0 + b.x1) / 2 - cx0, (b.y0 + b.y1) / 2 - cy0) <= mergeDist);
  const area = grp.reduce((s, b) => s + b.area, 0);
  if (area < areaMin) return { player: null, retry: retry > 150, blobs: blobs.length, maxArea: area };
  const box = { x0: Math.min(...grp.map(b => b.x0)), x1: Math.max(...grp.map(b => b.x1)), y0: Math.min(...grp.map(b => b.y0)), y1: Math.max(...grp.map(b => b.y1)) };
  return { player: { x: Math.round((box.x0 + box.x1) / 2), y: Math.round((box.y0 + box.y1) / 2), area, box }, retry: retry > 150, blobs: blobs.length };
}

// ---- v3: 動く足場をテンプレートで探して消してから、自機を探す ----
// 足場「[===]」は背景画像で x=304..359, y=245..258(1面)。毎コマ、その帯を横に走査して一番重なる位置を消す。
export function makePlatformTemplate(bgBuf, box = { x0: 304, x1: 359, y0: 245, y1: 258 }) {
  const { w, g } = readGray(bgBuf); const pts = [];
  for (let y = box.y0; y <= box.y1; y++) for (let x = box.x0; x <= box.x1; x++) if (g[y * w + x] < 300) pts.push([x - box.x0, y - box.y0]);
  return { pts, bw: box.x1 - box.x0 + 1, bh: box.y1 - box.y0 + 1, y0: box.y0 };
}

export function findPlatform(gray, w, h, tpl, yRange = 6) {
  let best = { score: -1 };
  for (let dy = -yRange; dy <= yRange; dy++) {
    const oy = tpl.y0 + dy; if (oy < 0 || oy + tpl.bh > h) continue;
    for (let ox = 0; ox + tpl.bw <= w; ox++) {
      let sc = 0; for (const [px, py] of tpl.pts) if (gray[(oy + py) * w + ox + px] < 300) sc++;
      if (sc > best.score) best = { score: sc, x0: ox, y0: oy, x1: ox + tpl.bw - 1, y1: oy + tpl.bh - 1 };
    }
  }
  best.ratio = best.score / tpl.pts.length;
  return best;
}

export function perceive3(buf, bg, tpl, { areaMin = 30, mergeDist = 40, margin = 3 } = {}) {
  const { w, h, g } = readGray(buf);
  const plat = findPlatform(g, w, h, tpl);
  const masked = (x, y) => plat.ratio > 0.6 && x >= plat.x0 - margin && x <= plat.x1 + margin && y >= plat.y0 - margin && y <= plat.y1 + margin;
  let retry = 0; for (let y = 0; y <= 40; y++) for (let x = 520; x < w; x++) if (g[y * w + x] < 300) retry++;
  const fg = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = y * w + x;
    if (g[i] < 300 && bg.g[i] - g[i] > 150 && !masked(x, y) && !(y <= 40 && x >= 520)) fg[i] = 1;
  }
  const seen = new Uint8Array(w * h); const blobs = [];
  for (let i = 0; i < w * h; i++) {
    if (!fg[i] || seen[i]) continue;
    let minx = 1e9, maxx = -1, miny = 1e9, maxy = -1, area = 0; const st = [i]; seen[i] = 1;
    while (st.length) {
      const k = st.pop(); const x = k % w, y = (k / w) | 0; area++;
      if (x < minx) minx = x; if (x > maxx) maxx = x; if (y < miny) miny = y; if (y > maxy) maxy = y;
      for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
        const xx = x + dx, yy = y + dy; if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
        const kk = yy * w + xx; if (fg[kk] && !seen[kk]) { seen[kk] = 1; st.push(kk); }
      }
    }
    blobs.push({ area, x0: minx, x1: maxx, y0: miny, y1: maxy });
  }
  const cand = blobs.filter(b => b.area >= 8).sort((a, b) => b.area - a.area);
  const base = { retry: retry > 150, platform: plat.ratio > 0.6 ? { x0: plat.x0, x1: plat.x1, y0: plat.y0, y1: plat.y1, ratio: +plat.ratio.toFixed(2) } : null };
  if (!cand.length) return { ...base, player: null };
  const c0 = cand[0]; const cx0 = (c0.x0 + c0.x1) / 2, cy0 = (c0.y0 + c0.y1) / 2;
  const grp = cand.filter(b => Math.hypot((b.x0 + b.x1) / 2 - cx0, (b.y0 + b.y1) / 2 - cy0) <= mergeDist);
  const area = grp.reduce((s, b) => s + b.area, 0);
  if (area < areaMin) return { ...base, player: null, maxArea: area };
  const box = { x0: Math.min(...grp.map(b => b.x0)), x1: Math.max(...grp.map(b => b.x1)), y0: Math.min(...grp.map(b => b.y0)), y1: Math.max(...grp.map(b => b.y1)) };
  return { ...base, player: { x: Math.round((box.x0 + box.x1) / 2), y: Math.round((box.y0 + box.y1) / 2), area, box } };
}
