# 基本ロール Owner/Editor/Viewer → Admin/Writer/Reader の移行の検証

記事: 「Editorはもう古い。新ロールへ安全に移る768試行」(Zenn)

- `PLAN.md` 検証計画(測定前に登録し、変更は末尾の変更履歴に記録)
- `REPRODUCE.md` 再現手順
- `find_legacy_impact.py` 影響の洗い出しスクリプト(= `scripts/e6_find.py`)
- `scripts/` 測定のスクリプト一式
- `data/` 生データ(プロジェクト ID・番号・メールアドレスは伏せ字)

| 実験 | 中身 | 主なファイル |
|---|---|---|
| E0 | ロール定義の揺れ | data/e0_*.csv, data/e0_sets/ |
| E1 | 新旧ロールの権限の差分 | data/e1_diff.csv, data/e1_dangerous.csv |
| E2 | 条件付きの付与(旧ロールは拒否) | data/e2_conditions_* |
| E3 | 32の操作 × 8主体 × 3回 | data/e3_main.jsonl, data/e3_owner_rfg_redo.jsonl |
| E4 | 条件の効き方(期限、名前、書き方) | data/e4_*.jsonl, data/e4b.jsonl |
| E5 | 付与と取り消しの反映時間、置き換えの順番 | data/e5*.jsonl |
| E6 | 洗い出しスクリプトの評価(乱数の仕掛け2回) | data/e6_*.jsonl, data/e6_plant_*.json |
| E7 | Asset Inventory と監査ログの見え方 | data/e7_* |

`python3 scripts/report.py` で記事の主要な数字が出ます。

個人の検証で、所属組織の見解ではありません。スクリプトは自分の検証用プロジェクトで動かしてください。
