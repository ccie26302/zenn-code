// 指示文と質問の数で kev-4b の応答時間がどう変わるか。試走 demo_laya_labeled の状態12件(毎回違う状態なのでキャッシュは効かない)で測る
// usage: node bench/kev_prompt_length.mjs → data/bench/kev_prompt_length.json
import fs from "node:fs";
const src = fs.readFileSync(new URL("../harness/run_demo.mjs", import.meta.url), "utf8");
const grab = (name) => eval("(" + src.slice(src.indexOf(`const ${name} = `) + `const ${name} = `.length, src.indexOf("};", src.indexOf(`const ${name} = `)) + 1).replace(/\$\{DECISION_FRAMES\}/g, "8") + ")");
const DESC = grab("DESC"), INSTR = grab("INSTR_RULES");
const eps = fs.readFileSync(new URL("../data/play/demo_laya_labeled/episodes.jsonl", import.meta.url), "utf8").trim().split("\n").map(JSON.parse);
const states = eps.flatMap(e => e.decisionsLog.map(d => d.state)).filter((_, i) => i % 7 === 0).slice(0, 12);   // 回をまたいで12件
const chars = states.map(s => JSON.stringify(s).length).sort((a, b) => a - b);
const crit = Object.fromEntries(Object.keys(DESC).map(k => [k, k]));
const out = {};
async function run(name, mk) { const v = []; for (const s of states) { const t = performance.now(); await (await fetch("http://127.0.0.1:8009/v1/systemone", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(mk(s)) })).json(); v.push(Math.round(performance.now() - t)); } v.sort((a, b) => a - b); out[name] = { n: v.length, p50: v[6], min: v[0], max: v.at(-1) }; console.log(name, out[name]); }
await run("参考デモ方式(長い指示文＋選択肢の説明＋質問3つ)", s => ({ state: s, model: "latest", questions: { next_action: { type: "choice", instructions: INSTR, criteria: DESC }, jump_needed: { type: "noul", instructions: "Should a forward jump begin or remain held now?" }, danger: { type: "score", instructions: "How dangerous?", criteria: ["Safe", "Soon", "Immediate"] } } }));
await run("長い指示文＋選択肢の説明・質問1つ", s => ({ state: s, model: "latest", questions: { next_action: { type: "choice", instructions: INSTR, criteria: DESC } } }));
await run("短い指示・質問1つ(状態は同じ JSON)", s => ({ state: s, model: "latest", questions: { next_action: { type: "choice", instructions: "Which action next?", criteria: crit } } }));
out.state_json_chars_p50 = chars[6];
fs.writeFileSync(new URL("../data/bench/kev_prompt_length.json", import.meta.url), JSON.stringify(out, null, 1));
