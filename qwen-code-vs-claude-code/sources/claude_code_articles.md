# 「Claude Code で端末上の作業をした」公開記事(下調べ、2026-10-16 閲覧)

WebFetch で本文を確かめたものだけを載せる。記事の主張は筆者が確かめたものではない。記事の多くは、人が対話で承認しながら動かした例で、プロンプト・モデル・版・成功率は書かれていない(N=1 のデモが中心で、成功した例だけが記事になっている可能性がある)。

課題への対応づけの規則: 2件以上の記事に出てくる作業の型を優先して課題にした(1件でも、Google Cloud・Terraform と、機械で判定できる音声の正規化は採った)。採らなかった型は末尾に書く。

## 出典(記号は課題の ID と区別するため src- を付ける)

| 記号 | 作業 | URL |
|---|---|---|
| src-V1 | フレーム抽出、16kHz WAV 抽出、Whisper で SRT、9:16、字幕焼き込み、BGM 差し替え、3倍速 | https://www.issoh.co.jp/tech/details/12534/ |
| src-V2 | 無音・フィラーのジェットカット、ass 字幕の焼き込み | https://fyve.co.jp/claude-code/articles/claude-code-video-cut-telop |
| src-V3 | 無音カット、SRT の整形、縦長変換、一括処理 | https://book.st-hakky.com/docs/claude-code-video-editing-automation |
| src-V4 | 無音・言い直しの除去、ノイズ除去、サムネイル、投稿 | https://learnwithhasan.com/guide/how-to-edit-videos-with-claude-code/ |
| src-V5 | 1MB 以下の GIF(2段階) | https://library.libecity.com/articles/01KV1PBX5JNP5E4457B3V4DD95 |
| src-V6 | 無劣化結合、scale と pad、CRF、切り出し | https://claudearchitectcertification.com/blog/2026-05-02-claude-code-automates-ffmpeg.md |
| src-V7 | 16kHz 抽出、BGM のミックス、単語単位の文字起こし | https://www.mejba.me/blog/claude-code-video-editing-workflow |
| src-V8 | スライドと音声から MP4 | https://library.libecity.com/articles/01KPD15QYPR5RT9AXXPJK9TPBF |
| src-V9 | MP3 化、H.265 化、解像度変換、pandoc | https://www.trustinsights.ai/blog/2026/07/ai-command-line-tools-part-2/ |
| src-A1 | 音声の抽出→文字起こし→要約、長い動画の分割 | https://fyve.co.jp/claude-code/articles/claude-code-video-transcribe-summary |
| src-A2 | whisper.cpp で SRT | https://claudecodeformarketers.com/blog/subtitle-videos-with-claude-code/ |
| src-A3 | ポッドキャストの音量レベリング | https://www.macstories.net/club/macstories-weekly-issue-497/unexpected-lessons-from-claude-code-experiments/ |
| src-I1 | 写真の撮影日での一括リネーム | https://library.libecity.com/articles/01KNWMRZQBBG7NEZHR6YPV7T5X |
| src-I2 | IPTC キーワードの書き込み | https://dev.classmethod.jp/articles/claude-code-bulk-photo-iptc-keywords-automation/ |
| src-I3 | AVIF / WebP / JPEG の複数幅、サイズ上限 | https://claudecode-lab.com/blog/claude-code-image-optimization/ |
| src-P1 | PDF のテキスト・表の抽出、OCR、結合・分割 | https://aurant-technologies.com/blog/blog-pdf-auto/ |
| src-P2 | pdftotext が無いときに PyMuPDF で代替 | https://dev.classmethod.jp/articles/claude-code-pdf-tools-pdftotext-pdfinfo-pymupdf/ |
| src-P3 | Anthropic 公式の PDF スキル | https://github.com/anthropics/skills/blob/main/skills/pdf/SKILL.md |
| src-D1 | 売上 CSV の分析、xlsx の複数シート | https://aurant-technologies.com/blog/blog-excel-analysis/ |
| src-D2 | グラフを xlsx に挿入 | https://aurant-technologies.com/?p=20220 |
| src-D3 | 祝日 CSV の月別集計 | https://crystal-method.com/blog/claude-code-non-engineer/ |
| src-D4 | SQLite でのデータ探索、スクレイピング | https://simonwillison.net/2026/Mar/16/coding-agents-for-data-analysis/ |
| src-D5 | Shift-JIS から UTF-8 への変換 | https://claudelab.net/articles/claude-code/claude-code-japanese-file-mojibake-shift-jis-utf8-fix |
| src-D6 | SQLite でのクエリの試作 | https://www.deployhq.com/blog/using-claude-code-with-sqlite-prototype-queries-locally |
| src-F1 | ダウンロードフォルダの振り分け | https://claudecodehq.com/playbooks/auto-organize-downloads |
| src-F2 | 847 ファイルを 12 フォルダに分類 | https://sidsaladi.substack.com/p/the-complete-claude-101-guide-master |
| src-F3 | コード以外のフォルダの検索・再構成(公式) | https://code.claude.com/docs/en/common-workflows |
| src-G1 | PR 作成、worktree(公式) | https://code.claude.com/docs/en/common-workflows |
| src-G2 | コンフリクトの解消スキル | https://haacked.com/archive/2026/03/25/resolve-merge-conflicts/ |
| src-G3 | 方針ファイルでのコンフリクト解消 | https://claudecode-lab.com/en/blog/claude-code-git-conflict-resolution/ |
| src-G4 | CI のテスト失敗の自動修正 | https://zenn.dev/pepabo/articles/83d209cd82c67d |
| src-DK1 | Dockerfile の縮小と故障の修正 | https://computingforgeeks.com/claude-code-docker-guide/ |
| src-DK2 | Docker MCP で compose 生成 | https://docs.docker.com/guides/genai-claude-code-mcp/claude-code-mcp-guide |
| src-GC1 | Artifact Registry、Cloud Run のデプロイ、Secret Manager、ロールバック | https://claudecode-lab.com/en/blog/claude-code-gcp-cloud-run/ |
| src-GC2 | Cloud Build、Cloud Run、Functions、gsutil | https://claudecodeguides.com/claude-code-gcp-google-cloud-setup-and-deployment-guide/ |
| src-GC3 | Kubernetes の Pod の IP 枯渇の診断(Anthropic 社内事例) | https://claude.com/blog/how-anthropic-teams-use-claude-code |
| src-T1 | Terraform で S3 と CloudFront、plan のエラー修正、fmt と validate | https://aurant-technologies.com/blog/claude-review-16204/ |
| src-T2 | Terraform の未定義の変数のエラー修正 | https://dev.classmethod.jp/articles/claude-code-github-actions-setup-hcp-terraform/ |
| src-AW1 | AWS CLI で EC2 | https://dev.classmethod.jp/articles/koty-mousa-aws-learning-claude-code-setup/ |
| src-B1 | Playwright MCP | https://www.simonwillison.net/2025/Jul/1/using-playwright-mcp-with-claude-code |
| src-B2 | Playwright で抽出して JSONL | https://dev.to/claudeguide/automate-web-scraping-with-claude-code-2026-10e5 |
| src-B3 | Claude in Chrome(公式) | https://code.claude.com/docs/en/chrome |
| src-L1 | ログの形式の判定と集計 | https://ramnode.com/guides/series/claude-code/log-analysis |
| src-L2 | journalctl の要約 | https://pro.tecmint.com/analyze-linux-logs-with-claude-code/ |
| src-L3 | systemd の故障の修正 | https://pro.tecmint.com/debug-failed-systemd-service-claude-code/ |
| src-L4 | パイプでログを渡す(公式) | https://code.claude.com/docs/en/cli-reference |

## 課題との対応

| 課題 | 作業の型 | 出典 |
|---|---|---|
| M1 | 音声の抽出 | src-V1, V7, A1, A2 |
| M2 | 縦型への変換 | src-V1, V3, V6 |
| M3 | 無音カット | src-V2, V3, V4 |
| M7 | 音量の正規化 | src-A3 |
| M8 | 倍速 | src-V1 |
| M9 | 文字起こしで SRT | src-V1, V2, V3, A1, A2 |
| D1 | 集計とグラフ入り xlsx | src-D1, D2 |
| D3 | PDF の表の抽出 | src-P1, P3 |
| D5 | OCR | src-P1, P3 |
| D8 | 静的サイトからの抽出 | src-B2 |
| R_B1_01 ほか(前作の課題) | フォルダの振り分け、ログ集計、テスト修正、コンフリクト、SQLite、CLI ツール | src-F1, F2, L1, G2, G3, D6, P2 |
| G01〜G10 | gcloud での Google Cloud の操作 | src-GC1, GC2(Google Cloud の記事は、どれも人が見ながら1回動かした例で、最終状態を機械で判定した例は無い) |
| T1〜T6 | Terraform | src-T1, T2 |

採らなかった型: 字幕の焼き込み・無劣化結合・GIF・WebP(判定は作れるが、M 群の本数をレビューに従って絞ったため)、Docker(Docker-in-Docker が要る)、ブラウザ操作(Playwright の事前導入とページの用意が要る)、systemd、AWS CLI(Google Cloud に絞るため)。
