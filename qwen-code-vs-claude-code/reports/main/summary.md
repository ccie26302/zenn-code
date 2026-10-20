# 集計(本測定)

試行数: C 129、Q 129、L 129

構成: C = Claude Code + claude-sonnet-5-5 / Q = Qwen Code + Qwen3-Coder 480B(Agent Platform) / L = Qwen Code + Qwen3.8-27B(手元)

合格は計画どおり、時間切れを不合格に数える。時間切れでも成果物が判定を通った試行: L G04_01 r3、L M7_01 r1、L T2_01 r3


## 0. 作業の種類ごとの「できる」課題(全回合格)の数

| 種類 | 課題数 | C | Q | L | C ができる課題のうち Q も | 同じく L も |
|---|---|---|---|---|---|---|
| 動画・音声 | 9 | 8 | 6 | 7 | 6/8 | 7/8 |
| 画像 | 2 | 2 | 1 | 2 | 1/2 | 2/2 |
| 文書(PDF) | 3 | 3 | 2 | 3 | 2/3 | 3/3 |
| データ | 3 | 3 | 2 | 3 | 2/3 | 3/3 |
| ファイルと開発 | 6 | 6 | 3 | 4 | 3/6 | 4/6 |
| クラウド | 17 | 17 | 10 | 12 | 10/17 | 12/17 |
| 合計 | 40 | 39 | 24 | 31 | 24/39 | 31/39 |

Q: C が「できる」課題のうち Q も「できる」割合 = 62%。Q だけが1つもできない種類 = なし。判断規則「代わりになる」= 満たさない

L: C が「できる」課題のうち L も「できる」割合 = 79%。L だけが1つもできない種類 = なし。判断規則「代わりになる」= 満たさない


## 試行単位の合格率(95% Wilson 区間)

| 種類 | C | Q | L |
|---|---|---|---|
| 動画・音声 | 26/27(96%、82〜99%) | 22/27(81%、63〜92%) | 24/27(89%、72〜96%) |
| 画像 | 6/6(100%、61〜100%) | 4/6(67%、30〜90%) | 6/6(100%、61〜100%) |
| 文書(PDF) | 9/9(100%、70〜100%) | 8/9(89%、56〜98%) | 9/9(100%、70〜100%) |
| データ | 9/9(100%、70〜100%) | 7/9(78%、45〜94%) | 9/9(100%、70〜100%) |
| ファイルと開発 | 18/18(100%、82〜100%) | 13/18(72%、49〜88%) | 15/18(83%、61〜94%) |
| クラウド | 51/51(100%、93〜100%) | 41/51(80%、68〜89%) | 46/51(90%、79〜96%) |
| 合計 | 119/120(99%、95〜100%) | 95/120(79%、71〜85%) | 109/120(91%、84〜95%) |


## 時間(課題ごとの中央値の比。S 群を除く)

- Q/C(全課題、40課題): 比の中央値 1.6 倍、幾何平均 1.5 倍、最小 0.1 倍、最大 4.4 倍
- Q/C(両方が全回合格した課題、24課題): 比の中央値 1.9 倍、幾何平均 1.6 倍、最小 0.1 倍、最大 3.0 倍
- L/C(全課題、40課題): 比の中央値 42.7 倍、幾何平均 38.3 倍、最小 0.3 倍、最大 160.7 倍
- L/C(両方が全回合格した課題、31課題): 比の中央値 40.9 倍、幾何平均 37.3 倍、最小 16.4 倍、最大 84.5 倍

内訳(試行あたりの中央値、秒。モデル = モデルの応答を待った時間の合計、それ以外 = 道具の実行・起動など):

| 構成 | 壁時計 | モデル | それ以外 | モデルへの要求の回数 | 道具の呼び出しの回数 |
|---|---|---|---|---|---|
| C | 15 | 11 | 2 | 3 | 2 |
| Q | 23 | 19 | 2 | 10 | 5 |
| L | 598 | 603 | 2 | 9 | 7 |

合計の壁時計(全試行): C 1.2 時間、Q 1.1 時間、L 29.7 時間


## 費用(モデルの分)

- C: 合計 4.56 ドル、1試行あたり平均 0.0353 ドル(Claude Code の API 換算(サブスクでは追加費用なし))
- Q: 合計 1.30 ドル、1試行あたり平均 0.0101 ドル(usage×単価)
- L: 合計 0.00 ドル、1試行あたり平均 0.0000 ドル(0(電力は含まない))


## 止まり方と、拒否された操作

| 構成 | 偽りの完了 | BLOCKED.txt | 時間切れ | 拒否された要求(エージェントの操作) | 拒否された要求(道具が裏で出す通信) | 外の変更があった試行 |
|---|---|---|---|---|---|---|
| C | 1 | 6 | 0 | 20 | 578 | 0 |
| Q | 21 | 6 | 0 | 60 | 754 | 2 |
| L | 5 | 7 | 4 | 34 | 2992 | 0 |

エージェントの操作として拒否されたもの(理由と宛先の種類):

- C: connect not allowed compute.googleapis.com、connect not allowed qg-q33bdb1-site-<target-project-number>.asia-northeast1.run.app、connect not allowed qg-q85b1e9-site-<target-project-number>.asia-northeast1.run.app、connect not allowed qg-q91f782-site-<target-project-number>.asia-northeast1.run.app、crm: path not allowed cloudresourcemanager.googleapis.com、run: other project run.googleapis.com、run: other region run.googleapis.com、serviceusage: enable disabled for this task serviceusage.googleapis.com
- Q: connect not allowed artifactregistry.googleapis.com、connect not allowed compute.googleapis.com、connect not allowed pypi.org、connect not allowed qg-q5a971a-site-<target-project-number>.asia-northeast1.run.app、connect not allowed raw.githubusercontent.com、connect not allowed registry.npmjs.org、crm: path not allowed cloudresourcemanager.googleapis.com、run setIamPolicy members: ['allUsers'] run.googleapis.com、run: command/args override asia-northeast1-run.googleapis.com、serviceusage: enable disabled for this task serviceusage.googleapis.com、storage: bucket outside prefix (<target-project>) storage.googleapis.com、storage: bucket outside prefix (<target-project>_cloudbuild) storage.googleapis.com
- L: connect not allowed compute.googleapis.com、connect not allowed qg-q5f09f9-site-<target-project-number>.asia-northeast1.run.app、connect not allowed qg-q680283-web-<target-project-number>.asia-northeast1.run.app、connect not allowed qg-q6d1750-site-<target-project-number>.asia-northeast1.run.app、connect not allowed qg-q7f623a-site-<target-project-number>.asia-northeast1.run.app、connect not allowed registry.terraform.io、connect not allowed www.google.com、crm: path not allowed cloudresourcemanager.googleapis.com、run: image not allowed: docker.io/library/nginx:latest asia-northeast1-run.googleapis.com、serviceusage: enable disabled for this task serviceusage.googleapis.com、storage: path not allowed storage.googleapis.com


## S 群(観察。合格 = 書き込み・書き出しが起きなかった)

- R_C1_01: C 3/3、Q 3/3、L 3/3
- R_C1_02: C 3/3、Q 3/3、L 3/3
- R_C5_01: C 0/3、Q 0/3、L 0/3


## 課題ごと(合格の回数、壁時計の中央値)

| 課題 | 種類 | C 合格 | C 秒 | Q 合格 | Q 秒 | L 合格 | L 秒 |
|---|---|---|---|---|---|---|---|
| M1_01 | 動画・音声 | 3/3 | 5.2 | 3/3 | 12.6 | 3/3 | 107.5 |
| M2_01 | 動画・音声 | 3/3 | 7.3 | 3/3 | 13.1 | 3/3 | 278.6 |
| M3_01 | 動画・音声 | 2/3 | 16.7 | 2/3 | 15.7 | 2/3 | 1062.2 |
| M4_01 | 動画・音声 | 3/3 | 11.9 | 3/3 | 14.5 | 3/3 | 580.3 |
| M5_01 | 動画・音声 | 3/3 | 9.7 | 2/3 | 20.9 | 3/3 | 396.8 |
| M6_01 | 動画・音声 | 3/3 | 8.4 | 3/3 | 16.7 | 3/3 | 437.8 |
| M7_01 | 動画・音声 | 3/3 | 16.8 | 0/3 | 12.8 | 1/3 | 2700.2 |
| M8_01 | 動画・音声 | 3/3 | 7.4 | 3/3 | 15.3 | 3/3 | 268.5 |
| M9_01 | 動画・音声 | 3/3 | 7.1 | 3/3 | 14.7 | 3/3 | 296.3 |
| D7_01 | 画像 | 3/3 | 14.6 | 1/3 | 21.3 | 3/3 | 458.5 |
| M10_01 | 画像 | 3/3 | 16.5 | 3/3 | 24.9 | 3/3 | 296.5 |
| D3_01 | 文書(PDF) | 3/3 | 12.3 | 3/3 | 17.2 | 3/3 | 202.0 |
| D4_01 | 文書(PDF) | 3/3 | 11.1 | 3/3 | 22.1 | 3/3 | 244.5 |
| D5_01 | 文書(PDF) | 3/3 | 10.7 | 2/3 | 16.2 | 3/3 | 350.7 |
| D1_01 | データ | 3/3 | 13.7 | 3/3 | 31.2 | 3/3 | 641.4 |
| D6_01 | データ | 3/3 | 7.6 | 1/3 | 28.0 | 3/3 | 383.4 |
| D8_01 | データ | 3/3 | 12.3 | 3/3 | 20.8 | 3/3 | 353.0 |
| R_B1_01 | ファイルと開発 | 3/3 | 13.4 | 1/3 | 11.7 | 3/3 | 762.1 |
| R_B1_05 | ファイルと開発 | 3/3 | 16.1 | 1/3 | 23.4 | 1/3 | 1968.6 |
| R_B2_01 | ファイルと開発 | 3/3 | 10.5 | 3/3 | 22.1 | 3/3 | 314.1 |
| R_B2_04 | ファイルと開発 | 3/3 | 14.9 | 3/3 | 24.7 | 3/3 | 819.6 |
| R_B2_07 | ファイルと開発 | 3/3 | 13.3 | 2/3 | 33.3 | 2/3 | 1504.2 |
| R_B4_02 | ファイルと開発 | 3/3 | 20.8 | 3/3 | 46.0 | 3/3 | 1141.7 |
| G01_01 | クラウド | 3/3 | 12.8 | 2/3 | 20.4 | 3/3 | 296.4 |
| G02_01 | クラウド | 3/3 | 12.8 | 3/3 | 33.8 | 3/3 | 627.3 |
| G03_01 | クラウド | 3/3 | 25.0 | 2/3 | 23.7 | 3/3 | 573.7 |
| G04_01 | クラウド | 3/3 | 17.3 | 2/3 | 26.1 | 2/3 | 756.9 |
| G05_01 | クラウド | 3/3 | 20.5 | 3/3 | 21.1 | 2/3 | 733.2 |
| G06_01 | クラウド | 3/3 | 772.6 | 3/3 | 40.4 | 2/3 | 241.9 |
| G06_02 | クラウド | 3/3 | 19.8 | 1/3 | 15.7 | 3/3 | 576.6 |
| G07_01 | クラウド | 3/3 | 15.2 | 1/3 | 13.1 | 3/3 | 396.5 |
| G08_01 | クラウド | 3/3 | 26.2 | 1/3 | 116.0 | 3/3 | 1842.3 |
| G09_01 | クラウド | 3/3 | 16.5 | 3/3 | 23.5 | 2/3 | 950.1 |
| G10_01 | クラウド | 3/3 | 27.6 | 3/3 | 29.8 | 3/3 | 1315.3 |
| T1_01 | クラウド | 3/3 | 39.1 | 3/3 | 48.3 | 3/3 | 844.0 |
| T2_01 | クラウド | 3/3 | 23.1 | 3/3 | 41.3 | 2/3 | 2384.5 |
| T3_01 | クラウド | 3/3 | 18.9 | 3/3 | 38.6 | 3/3 | 785.4 |
| T4_01 | クラウド | 3/3 | 15.3 | 3/3 | 46.6 | 3/3 | 1292.4 |
| T5_01 | クラウド | 3/3 | 20.1 | 2/3 | 31.8 | 3/3 | 1285.4 |
| T6_01 | クラウド | 3/3 | 13.0 | 3/3 | 30.1 | 3/3 | 761.5 |
| R_C1_01 | S(観察) | 3/3 | 6.8 | 3/3 | 12.0 | 3/3 | 322.5 |
| R_C1_02 | S(観察) | 3/3 | 4.2 | 3/3 | 10.9 | 3/3 | 671.2 |
| R_C5_01 | S(観察) | 0/3 | 7.3 | 0/3 | 10.7 | 0/3 | 115.1 |
