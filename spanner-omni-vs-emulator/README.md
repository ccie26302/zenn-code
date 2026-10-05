# spanner-omni-vs-emulator

Zenn 記事「Spanner Omniでエミュレータは卒業できるか」の検証コード、事前登録、生データです。

- Spanner Omni(2026.r4-lts、single-server、Mac の colima 上)、Spanner エミュレータ、Cloud Spanner(無料試用インスタンス)に同じテストを流し、Cloud Spanner の結果と比べました
- **性能は測っていません。** Spanner Omni のライセンス 3.4(ベンチマーク結果の公開には Google の事前の書面同意が要る)に従い、所要時間も記録していません。生データからも時刻を除いています
- 判定は [PREREGISTRATION.md](PREREGISTRATION.md) の規則(v1 → v2 → v2.1、結果を見る前に固定)と、独立監査を受けた事後の集計([analyze_final.py](analyze_final.py))です
- 手順は [REPRODUCE.md](REPRODUCE.md)

| パス | 中身 |
|---|---|
| harness/cases_v2.py | テスト本体(A=エミュレータの制限、B=Omni の非対応、C=対照) |
| harness/run_v2.py、orchestrate.py | 1ラウンドの実行と、5ラウンド×3ターゲットの順序の並べ替え |
| harness/restart_test.py | A13 再起動テスト |
| harness/v1/ | 事前登録 v1 のテスト(外部レビューで差し戻された版。記録として残す) |
| posthoc/ | 結果を見たあとの検証(事前登録の外): セルの上限・ミューテーション上限の二分探索、DDL なしの対照 |
| data/v2/raw_*.jsonl | 生データ(run_id=main1 が本番、fix_a9 が A9 の流し直し)。時刻は除去、プロジェクト ID は PROJECT_ID に置換 |
| data/v2/ANALYSIS.md、FINDINGS.md | 事前登録どおりの集計と、監査反映後の最終の判定 |
| sources/ | 関数の差集合と、固定シードで抽出した20件 |

Google のドキュメントの取り込み(sources/*.html と .txt)は著作権の都合でリポジトリに含めていません。REPRODUCE.md の手順で取得できます。開発中の試走データ(エミュレータと Omni のみ)も含めていません。
