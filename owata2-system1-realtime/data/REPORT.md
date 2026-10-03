# REPORT(report.py が生データから生成)

定義: 死亡(録画で生存を除く) = bench/death_check.py で、回の終了後の録画に自機が映っていた回(ポーズ中に見失った誤判定)を除いた数。崖の端 x≈185。跳んで崖を離れた = x>185 かつ y<300 の手がある。足場(判断時) = 判断の瞬間に接地・x 200〜380・y 215〜250。足場(録画) = bench/landing_from_rec.py(全コマで足場の上に10コマ以上連続)。向こう岸 = 接地・x≥385・y≥290 または crossed。見失い = 判断間で x が100px 以上飛んだ回(そこで打ち切り)。

## 1a. 最終比較(事前登録・全本英語・STATE_V=4・軽い罰・各100回×3本＋モデルだけ30回)

| TAG | 条件 | 回数 | 死亡 | 死亡(録画で生存を除く) | 崖の端より先(落下含む) | 跳んで崖を離れた | 足場(判断時) | 足場(録画) | 向こう岸 | 見失い | 最高 x | 遅れ p50(コマ) | モデル p50(ms) | 目 p50(ms) | 1位採用(11択の手のみ) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fin_kev_en_1 | kev-4b 英語 1本目 | 100 | 100 | 100 | 98 | 94 | 1 | 1 | 0 | 0 | 264 | 17 | 215 | 66 | 60% |
| fin_kev_en_2 | kev-4b 英語 2本目 | 100 | 98 | 98 | 96 | 90 | 3 | 3 | 0 | 0 | 336 | 16 | 203 | 66 | 52% |
| fin_kev_en_3 | kev-4b 英語 3本目 | 100 | 100 | 100 | 99 | 88 | 10 | 14 | 0 | 0 | 366 | 17 | 216 | 66 | 64% |
| fin_laya_en_1 | laya-ml 英語 1本目 | 100 | 71 | 64 | 47 | 42 | 20 | 23 | 0 | 8 | 312 | 6 | 29 | 65 | 57% |
| fin_laya_en_2 | laya-ml 英語 2本目 | 100 | 75 | 67 | 26 | 10 | 0 | 0 | 0 | 5 | 229 | 6 | 29 | 65 | 62% |
| fin_laya_en_3 | laya-ml 英語 3本目 | 100 | 84 | 80 | 64 | 57 | 0 | 0 | 0 | 6 | 238 | 6 | 29 | 66 | 43% |
| fin_kev_en_modelonly | kev-4b 英語 モデルだけ | 30 | 30 | 30 | 30 | 27 | 0 | 0 | 0 | 0 | 227 | 16 | 197 | 67 | 100% |
| fin_laya_en_modelonly | laya-ml 英語 モデルだけ | 30 | 0 | — | 0 | 0 | 0 | 0 | 0 | 0 | 99 | 6 | 27 | 65 | 100% |

## 1b. 開発中の試走(日本語・条件を順に変えながら1本ずつ)

| TAG | 条件 | 回数 | 死亡 | 死亡(録画で生存を除く) | 崖の端より先(落下含む) | 跳んで崖を離れた | 足場(判断時) | 足場(録画) | 向こう岸 | 見失い | 最高 x | 遅れ p50(コマ) | モデル p50(ms) | 目 p50(ms) | 1位採用(11択の手のみ) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rt2_layaml | laya-ml・禁止だけの記憶・11択(v2) | 100 | 21 | — | 0 | 0 | 0 | — | 0 | 2 | 129 | 4 | 26 | 46 | 100% |
| rt3_layaml_gain | laya-ml・良い記憶 1回目 | 100 | 31 | — | 1 | 0 | 0 | — | 0 | 0 | 186 | 4 | 22 | 46 | 76% |
| rt4_layaml_gain | laya-ml・良い記憶 調整後 | 100 | 94 | — | 46 | 33 | 0 | — | 0 | 0 | 256 | 4 | 23 | 46 | 24% |
| rt5_layaml_gain_rec | laya-ml・同上＋録画(呼び方 v2) | 100 | 93 | — | 42 | 29 | 1 | 1 | 0 | 3 | 252 | 5 | 29 | 60 | 24% |
| rt6_layaml_v3_rec | laya-ml・大ジャンプを「ジャンプ」と呼ぶ(v3) | 100 | 98 | — | 88 | 72 | 27 | 31 | 0 | 0 | 381 | 5 | 29 | 60 | 46% |
| rt10_layaml_ban_rec | laya-ml・rt6 と同じ設定の回し直し | 100 | 93 | — | 74 | 64 | 1 | 2 | 0 | 2 | 360 | 6 | 29 | 64 | 33% |
| rt7_layaml_noban_rec | laya-ml・禁止なし | 100 | 100 | — | 93 | 75 | 3 | 4 | 0 | 0 | 345 | 6 | 29 | 65 | 44% |
| rt8_layaml_noban_eye_rec | laya-ml・禁止なし＋トゲの目 | 100 | 85 | — | 78 | 54 | 2 | 3 | 0 | 1 | 238 | 6 | 30 | 66 | 36% |
| rt11_layaml_softpen_rec | laya-ml・軽い罰 | 100 | 94 | — | 84 | 67 | 10 | 20 | 1 | 1 | 397 | 6 | 29 | 65 | 30% |
| rt9_layaml_modelonly_eye_rec | laya-ml・モデルだけ(記憶なし) | 30 | 0 | — | 0 | 0 | 0 | — | 0 | 0 | 125 | 6 | 30 | 66 | 100% |
| rt12_kev_modelonly_goal_rec | kev-4b・モデルだけ・ゴール明示 | 30 | 30 | — | 30 | 0 | 0 | — | 0 | 0 | 198 | 17 | 218 | 67 | 100% |
| rt13_kev_softpen_goal_rec | kev-4b・軽い罰・ゴール明示 | 100 | 98 | — | 96 | 82 | 4 | 4 | 0 | 0 | 282 | 17 | 218 | 64 | 51% |
| rt14_layaml_softpen_goal_rec | laya-ml・軽い罰・ゴール明示 | 100 | 98 | — | 94 | 88 | 46 | 47 | 0 | 0 | 354 | 6 | 30 | 66 | 35% |

足場に乗った回の推移(25回ごと、判断時 / 録画):

- fin_kev_en_1: 0 → 0 → 1 → 0  / 録画 0 → 0 → 1 → 0
- fin_kev_en_2: 0 → 0 → 2 → 1  / 録画 0 → 0 → 2 → 1
- fin_kev_en_3: 0 → 2 → 4 → 4  / 録画 0 → 3 → 5 → 6
- fin_laya_en_1: 0 → 0 → 8 → 12  / 録画 0 → 0 → 8 → 15
- fin_laya_en_2: 0 → 0 → 0 → 0  / 録画 0 → 0 → 0 → 0
- fin_laya_en_3: 0 → 0 → 0 → 0  / 録画 0 → 0 → 0 → 0
- fin_kev_en_modelonly: 0 → 0  / 録画 0 → 0
- fin_laya_en_modelonly: 0 → 0  / 録画 0 → 0
- rt2_layaml: 0 → 0 → 0 → 0
- rt3_layaml_gain: 0 → 0 → 0 → 0
- rt4_layaml_gain: 0 → 0 → 0 → 0
- rt5_layaml_gain_rec: 0 → 1 → 0 → 0  / 録画 0 → 1 → 0 → 0
- rt6_layaml_v3_rec: 5 → 13 → 3 → 6  / 録画 6 → 15 → 3 → 7
- rt10_layaml_ban_rec: 0 → 1 → 0 → 0  / 録画 0 → 1 → 1 → 0
- rt7_layaml_noban_rec: 0 → 0 → 0 → 3  / 録画 0 → 1 → 0 → 3
- rt8_layaml_noban_eye_rec: 0 → 0 → 2 → 0  / 録画 0 → 1 → 2 → 0
- rt11_layaml_softpen_rec: 0 → 0 → 4 → 6  / 録画 0 → 0 → 7 → 13
- rt9_layaml_modelonly_eye_rec: 0 → 0
- rt12_kev_modelonly_goal_rec: 0 → 0
- rt13_kev_softpen_goal_rec: 0 → 0 → 0 → 4  / 録画 0 → 0 → 0 → 4
- rt14_layaml_softpen_goal_rec: 1 → 13 → 17 → 15  / 録画 1 → 13 → 17 → 16

向こう岸に着いた回: {'rt11_layaml_softpen_rec': [62]}

崖際(x 150〜186・接地)の判断と、そこから「右へジャンプ」して7手以内に足場(判断時)に乗った割合:

- fin_kev_en_1: 崖際の判断 95 回(上位 [('rightjump_big', 86), ('right', 7), ('jump_big', 1)])、右へジャンプ→足場 1/86
- fin_kev_en_2: 崖際の判断 172 回(上位 [('rightjump_big', 85), ('wait', 77), ('right', 4)])、右へジャンプ→足場 3/85
- fin_kev_en_3: 崖際の判断 105 回(上位 [('right', 77), ('rightjump_big', 28)])、右へジャンプ→足場 2/28
- fin_laya_en_1: 崖際の判断 421 回(上位 [('attack', 306), ('wait', 72), ('rightjump_big', 11)])、右へジャンプ→足場 1/11
- fin_laya_en_2: 崖際の判断 212 回(上位 [('wait', 104), ('attack', 64), ('left', 17)])、右へジャンプ→足場 0/11
- fin_laya_en_3: 崖際の判断 232 回(上位 [('attack', 151), ('wait', 72), ('leftjump_big', 3)])、右へジャンプ→足場 0/3
- fin_kev_en_modelonly: 崖際の判断 42 回(上位 [('right', 31), ('rightjump_big', 11)])、右へジャンプ→足場 0/11
- fin_laya_en_modelonly: 崖際の判断 0 回(上位 [])、右へジャンプ→足場 0/0
- rt7_layaml_noban_rec: 崖際の判断 50 回(上位 [('rightjump_big', 18), ('jump_big', 11), ('right', 9)])、右へジャンプ→足場 3/18
- rt8_layaml_noban_eye_rec: 崖際の判断 233 回(上位 [('wait', 123), ('attack', 77), ('jump_big', 9)])、右へジャンプ→足場 0/4
- rt12_kev_modelonly_goal_rec: 崖際の判断 66 回(上位 [('right', 66)])、右へジャンプ→足場 0/0
- rt13_kev_softpen_goal_rec: 崖際の判断 233 回(上位 [('wait', 78), ('rightjump_big', 77), ('right', 51)])、右へジャンプ→足場 4/77
- rt14_layaml_softpen_goal_rec: 崖際の判断 45 回(上位 [('right', 19), ('leftjump_big', 10), ('jump_big', 8)])、右へジャンプ→足場 0/0

最終比較: 崖際の「右へジャンプ」を、判断時の足場の位置(キーの4番目 = (足場の左端−自機x)/32 の整数部＋向き l/r/s)ごとに(成功/回数):

- kev-4b: 1l 0/181, 1r 0/6, 1s 0/1, 2l 0/1, 2r 4/7, 3r 1/2, 4r 1/1
- laya-ml: 1l 0/3, 2l 0/5, 2r 0/2, 3l 0/7, 3r 0/3, 4r 1/4, 5r 0/1

足場(録画)の閾値の感度(10コマ以上 / 20コマ以上):

- fin_kev_en_1: 1 / 1(判定対象 96 回)
- fin_kev_en_2: 3 / 3(判定対象 93 回)
- fin_kev_en_3: 14 / 13(判定対象 91 回)
- fin_laya_en_1: 23 / 10(判定対象 43 回)
- fin_laya_en_2: 0 / 0(判定対象 15 回)
- fin_laya_en_3: 0 / 0(判定対象 60 回)
- fin_kev_en_modelonly: 0 / 0(判定対象 26 回)
- fin_laya_en_modelonly: 0 / 0(判定対象 0 回)

遅れなしで続けて押した場合(m_feasible.mjs): 待ちコマ数×空中で右の回数 124 通り中 31 通りで足場に乗れた

## 2. 呼び方の効果(最初の判断での確率、スタート地点)

- rt5_layaml_gain_rec: rightjump_big=0.03 jump_big=0.088 1位=jump_small
- rt6_layaml_v3_rec: rightjump_big=0.073 jump_big=0.188 1位=jump_big

## 3. 応答時間ベンチ(Mac M4 Max から・直列・keep-alive)

| 対象 | N | p50 | p90 | p99 | 最大 | 60fps のコマ数(p50) | サーバ内訳 p50 |
|---|---|---|---|---|---|---|---|
| gemini-2.5-flash_vertex_tokyo | 300 | 439.7 | 520.19 | 615.13 | 660.35 | 26.4 |  |
| gemini-3.8-flash_vertex_global_low | 100 | 3685.16 | 19067.62 | 61886.64 | 61886.64 | 221.1 |  |
| kev-4b_mlx_mac | 300 | 200.12 | 207.77 | 214.33 | 214.75 | 12.0 |  |
| kev-4b_vertex_kev-l4-uscentral1 | 300 | 251.65 | 333.55 | 417.07 | 474.65 | 15.1 | gpu_ms=84.4 app_ms=88.5 remote_ms=250.12 |
| laya-ml_cpu_mac | 300 | 53.65 | 57.45 | 59.38 | 61.06 | 3.2 |  |
| laya-ml_mps_mac | 300 | 14.57 | 15.0 | 16.0 | 16.5 | 0.9 |  |

目(N=300): 撮影 p50 31.84 / 判定往復 p50 23.22 / 合計 p50 55.25 p90 65.19 p99 77.99
  判定の内訳 p50: {'decode': 1.541, 'player': 12.016, 'camera': 2.314, 'platform': 3.052, 'ground': 0.06, 'spikes': 3.325}

ネットワーク net_asia-northeast1-aiplatform_googleapis_com_20261002-172542.csv N=50: {'dns_ms': 3.8, 'tcp_ms': 7.37, 'tls_ms': 13.68, 'ttfb_ms': 40.49}

ネットワーク net_vertex_dedicated_endpoint_us-central1_20261002-192112.csv N=50: {'dns_ms': 3.02, 'tcp_ms': 9.42, 'tls_ms': 54.07, 'ttfb_ms': 232.65}

60秒放置後(kev-4b_vertex_kev-l4-uscentral1_idle60s_20261002-193140.csv): [633.6, 334.5, 383.4, 354.0, 463.1, 409.6, 412.5, 418.0, 408.8, 400.6]

kev-4b_vertex_kev-l4-uscentral1_20261002-192112.csv: ネットワーク＋入口(remote−app) p50 160.2 p90 241.4 最小 141.2

## 4. 文章の実験

### probe_models.json
```
{
 "laya-ml/G0F0": {
  "右へジャンプの確率 平均": 0.095,
  "1位の内訳": {
   "jump_big": 8,
   "left": 8
  },
  "足場が右へ動く場面で1位が左系": "0/8",
  "足場が左へ動く場面で1位が左系": "8/8"
 },
 "laya-ml/G1F1": {
  "右へジャンプの確率 平均": 0.086,
  "1位の内訳": {
   "jump_big": 8,
   "left": 8
  },
  "足場が右へ動く場面で1位が左系": "0/8",
  "足場が左へ動く場面で1位が左系": "8/8"
 },
 "kev-4b/G0F0": {
  "右へジャンプの確率 平均": 0.188,
  "1位の内訳": {
   "right": 16
  },
  "足場が右へ動く場面で1位が左系": "0/8",
  "足場が左へ動く場面で1位が左系": "0/8"
 },
 "kev-4b/G1F1": {
  "右へジャンプの確率 平均": 0.233,
  "1位の内訳": {
   "right": 10,
   "rightjump_big": 6
  },
  "足場が右へ動く場面で1位が左系": "0/8",
  "足場が左へ動く場面で1位が左系": "0/8"
 }
}
```
### probe_models2.json
```
{
 "laya-ml/呼び方v2×並びv2": {
  "右へ大ジャンプの確率 平均": 0.036,
  "その場で大ジャンプの確率 平均": 0.054,
  "1位の内訳": {
   "left": 16
  }
 },
 "laya-ml/呼び方v3×並びv2": {
  "右へ大ジャンプの確率 平均": 0.133,
  "その場で大ジャンプの確率 平均": 0.106,
  "1位の内訳": {
   "left": 8,
   "rightjump_big": 6,
   "leftjump_big": 2
  }
 },
 "laya-ml/呼び方v2×並びv3": {
  "右へ大ジャンプの確率 平均": 0.034,
  "その場で大ジャンプの確率 平均": 0.114,
  "1位の内訳": {
   "left": 16
  }
 },
 "laya-ml/呼び方v3×並びv3": {
  "右へ大ジャンプの確率 平均": 0.095,
  "その場で大ジャンプの確率 平均": 0.165,
  "1位の内訳": {
   "jump_big": 8,
   "left": 8
  }
 },
 "laya-ml/向きの書き方=左へ・右へ": {
  "「左」相当の場面で1位が左系": "8/8",
  "「右」相当の場面で1位が左系": "0/8",
  "1位の内訳": {
   "jump_big": 8,
   "left": 8
  }
 },
 "laya-ml/向きの書き方=xが減る・増える": {
  "「左」相当の場面で1位が左系": "0/8",
  "「右」相当の場面で1位が左系": "0/8",
  "1位の内訳": {
   "jump_big": 16
  }
 },
 "kev-4b/呼び方v2×並びv2": {
  "右へ大ジャンプの確率 平均": 0.093,
  "その場で大ジャンプの確率 平均": 0.059,
  "1位の内訳": {
   "right": 16
  }
 },
 "kev-4b/呼び方v3×並びv2": {
  "右へ大ジャンプの確率 平均": 0.222,
  "その場で大ジャンプの確率 平均": 0.066,
  "1位の内訳": {
   "right": 15,
   "rightjump_big": 1
  }
 },
 "kev-4b/呼び方v2×並びv3": {
  "右へ大ジャンプの確率 平均": 0.157,
  "その場で大ジャンプの確率 平均": 0.066,
  "1位の内訳": {
   "right": 16
  }
 },
 "kev-4b/呼び方v3×並びv3": {
  "右へ大ジャンプの確率 平均": 0.188,
  "その場で大ジャンプの確率 平均": 0.064,
  "1位の内訳": {
   "right": 16
  }
 },
 "kev-4b/向きの書き方=左へ・右へ": {
  "「左」相当の場面で1位が左系": "0/8",
  "「右」相当の場面で1位が左系": "0/8",
  "1位の内訳": {
   "right": 16
  }
 },
 "kev-4b/向きの書き方=xが減る・増える": {
  "「左」相当の場面で1位が左系": "0/8",
  "「右」相当の場面で1位が左系": "0/8",
  "1位の内訳": {
   "right": 10,
   "rightjump_big": 6
  }
 }
}
```
### probe_models_en.json
```
{
 "laya-ml/G0F0/left・right": {
  "jump to the right の確率 平均": 0.089,
  "1位の内訳": {
   "attack": 16
  },
  "左向きの場面で1位が左系": "0/8",
  "右向きの場面で1位が左系": "0/8"
 },
 "laya-ml/G1F1/left・right": {
  "jump to the right の確率 平均": 0.047,
  "1位の内訳": {
   "attack": 16
  },
  "左向きの場面で1位が左系": "0/8",
  "右向きの場面で1位が左系": "0/8"
 },
 "laya-ml/G0F0/x decreasing・increasing": {
  "jump to the right の確率 平均": 0.061,
  "1位の内訳": {
   "attack": 16
  },
  "左向きの場面で1位が左系": "0/8",
  "右向きの場面で1位が左系": "0/8"
 },
 "kev-4b/G0F0/left・right": {
  "jump to the right の確率 平均": 0.249,
  "1位の内訳": {
   "rightjump_big": 13,
   "right": 3
  },
  "左向きの場面で1位が左系": "0/8",
  "右向きの場面で1位が左系": "0/8"
 },
 "kev-4b/G1F1/left・right": {
  "jump to the right の確率 平均": 0.28,
  "1位の内訳": {
   "rightjump_big": 9,
   "right": 7
  },
  "左向きの場面で1位が左系": "0/8",
  "右向きの場面で1位が左系": "0/8"
 },
 "kev-4b/G0F0/x decreasing・increasing": {
  "jump to the right の確率 平均": 0.212,
  "1位の内訳": {
   "rightjump_big": 8,
   "right": 8
  },
  "左向きの場面で1位が左系": "0/8",
  "右向きの場面で1位が左系": "0/8"
 }
}
```

## 足場の速さ
```
{"区間の数": 2829, "px/コマ 中央値": 2.0, "四分位": [2.0, 2.15]}
```

## 5. 目の検証 eye_validation.json
```
{
 "自機": {
  "ラベル×判定": {
   "absent→なし": 69,
   "alive→あり": 95,
   "dying→なし": 22
  },
  "score": {
   "alive": {
    "min": 0.493,
    "max": 1.0
   },
   "dying": {
    "min": 0.357,
    "max": 0.357
   },
   "absent": {
    "min": 0.357,
    "max": 0.357
   }
  },
  "閾値": 0.43,
  "注": "ラベル alive=生存 / absent=自機なし / dying=死亡演出。目視1名・1面のみ"
 },
 "トゲの列": {
  "コマ数": 6556,
  "列の本数ごとのコマ数": {
   "1": 6542,
   "0": 14
  },
  "1本以外のコマ": [
   "data/play/rt5_layaml_gain_rec/rec/ep42/00189.png",
   "data/play/rt5_layaml_gain_rec/rec/ep42/00196.png",
   "data/play/rt5_layaml_gain_rec/rec/ep42/00203.png",
   "data/play/rt5_layaml_gain_rec/rec/ep42/00210.png",
   "data/play/rt5_layaml_gain_rec/rec/ep42/00217.png",
   "data/play/rt5_layaml_gain_rec/rec/ep42/00224.png",
   "data/play/rt5_layaml_gain_rec/rec/ep42/00231.png",
   "data/play/rt5_layaml_gain_rec/rec/ep42/00238.png",
   "data/play/rt5_layaml_gain_rec/rec/ep42/00245.png",
   "data/play/rt5_layaml_gain_rec/rec/ep42/00252.png",
   "data/play/rt5_layaml_gain_rec/rec/ep42/00259.png",
   "data/play/rt5_layaml_gain_rec/rec/ep42/00266.png",
   "data/play/rt5_layaml_gain_rec/rec/ep42/00273.png",
   "data/play/rt5_layaml_gain_rec/rec/ep42/00280.png"
  ],
  "注": "1面には穴が1つ。0本のコマはすべて樹海側でトゲが画面外か目視で確認する(確認結果は記事に記載)"
 }
}
```
