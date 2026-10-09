# gcp-leak-guard

Zenn 記事「漏えい続発の今、Google Cloudの備えは効くか実測」のスクリプトと実測データです。個人情報保護委員会の注意喚起(2026年10月改訂)が挙げる9つの事例のうち Google Cloud の設定で入れられる対策と、ランサムに備えるバックアップを1本のスクリプトにまとめ、効いているかを PASS / FAIL で確かめます。組織(Organization)のない個人や小規模のプロジェクトでも動くように書いています。

```bash
# 既存のプロジェクトに足す(費用はほとんどかからない。data は個人データ用のバケットを新設し、30日で自動削除)
PROJECT_ID=<本番のプロジェクト> GH_REPO=<owner/repo> ./baseline.sh apis data detect wif
# バックアップ(管理者の違う別のプロジェクト。ロックは元に戻せないので、最初は使い捨てのプロジェクトで短い期間で)
PROJECT_ID=<本番のプロジェクト> BACKUP_PROJECT=<別のプロジェクト> BACKUP_RETENTION=7d LOCK_BACKUP=1 ./baseline.sh backup
# 検証用のプロジェクトで全部入れて、効いているかを確かめる
export PROJECT_ID=<検証用のプロジェクト> BACKUP_PROJECT=<使い捨てのプロジェクト> GH_REPO=<owner/repo>
BACKUP_RETENTION=600s LOCK_BACKUP=1 REMOVE_DEFAULT_EDITOR=1 ./baseline.sh
./verify.sh
```

全部入れると課金が発生します。主にロードバランサの転送ルールと Cloud Armor のポリシーで、公開されている単価で計算すると、置いたままで月25ドル前後です。両方のプロジェクトでオーナー相当の権限が要ります。試したら [REPRODUCE.md](REPRODUCE.md) の手順で消してください。

| パス | 中身 |
|---|---|
| baseline.sh | 仕組みを入れるスクリプト。step ごとに流せる(`./baseline.sh data detect` など)。何度流しても同じ状態になる |
| verify.sh | 入れた仕組みが効いているかを、実際に操作して確かめる(公開を試して拒否されるか、消したファイルを戻せるか、上限を超えると 429 か、など) |
| dlp_mask.sh | Sensitive Data Protection で、LLM に渡す前の文章から個人情報を伏せる。`CUSTOM=0` で日本の携帯番号の customInfoType を外した比較ができる |
| app/ | ソースからデプロイする検証用のアプリ(ベースイメージの自動更新)。secret は値を返さず、読めたかと長さだけを返す |
| api/ | Dockerfile で作る検証用の API(週次の再ビルド、ロードバランサ＋Cloud Armor の後ろ)。UUID 以外の ID は 400 |
| data/alert_trial.sh | 試行用のアラートを作り(create)、15分以上おいてから、鍵の作成、allUsers の付与(Cloud Run と Cloud Storage)、IAM チェックの無効化を行って、監査ログの時刻から通知までを測る(run) |
| data/alerts.csv | アラートの実測(新しいインシデントの最初の通知)。記事の1〜3回目は trial 1・2・4(trial 3 は無効、alert_notes.txt) |
| data/alert_messages.csv | 届いた通知の一覧(発行時刻、ポリシー名、状態、インシデントの開始時刻)。生の通知は識別子を含むので公開していない |
| data/alert_compute.py | 生の通知と監査ログから alerts.csv の秒数を出す集計 |
| data/armor_timeline.sh / armor_timeline_final.txt / armor_timeline_v3.txt | 新しいロードバランサに30秒ごとに送り、応答し始める時刻と 429 が返り始める時刻を記録した(2つの新規プロジェクト) |
| data/alert_notes.txt | 計測の経緯。作った直後のポリシーが効かなかったこと、旧版が再通知を測っていたこと |
| data/alerts_reopened_incidents.csv | 旧版のデータ(開いたままのインシデントへの再通知を測っていた。記事では使っていない) |
| data/vuln_summary.json | Artifact Registry のスキャン結果の要約(1段階目) |
| data/vuln_stages.txt | Dockerfile の4段階ごとの件数と、修正版のある脆弱性の場所 |
| data/wif.txt | GitHub Actions からの WIF の結果(main と feature ブランチ) |
| data/armor.txt | Cloud Armor のレートリミットの結果と時系列(付けた直後は効いていなかった) |
| data/dlp.txt | DLP の customInfoType あり・なしの出力 |
| data/dlp_likelihood.txt | 組み込みの PHONE_NUMBER の確信度(単体と文の中) |
| data/backup_trial.sh | `SCRATCH_PROJECT` に指定した使い捨てのプロジェクトで、オーナー権限を取られた前提で、論理削除だけのバケットと、保持ポリシーをロックしたバケットを消しにいく(使い捨てのプロジェクトで) |
| data/backup.txt | その結果。B9〜B13(lien を外してプロジェクトを削除し、取り消す)は手で行った |
| data/backup_run1_lock_aborted.txt | 失敗した1回目。`--quiet` でロックが中断され、ロックされないまま進んでプロジェクトまで消せた |
| data/patch_runner_reach.txt | 週次ビルドの SA になりすまして届く範囲を確かめた結果(今の版と、旧版の広い権限を一時的に戻した対照、SA を指定しないビルドでの迂回) |
| data/fp_weekly.txt / fp_check.sh / fp_check2.sh / fp_check.txt | 週次の再デプロイで「IAM チェックの無効化」アラートが鳴った誤報、最初の直し方でなりすましがすり抜けた件、直したあとの確認 |
| data/alert_audit_events.csv | 監査ログの時刻と操作の種類(識別子を除いたもの) |
| data/final_run.log | 最終版の baseline.sh を新規の空のプロジェクトで流したログ(識別子は伏せた) |
| data/verify.txt | そのあとの verify.sh の出力 |

## step の中身

| step | 入るもの | 注意喚起の事例 |
|---|---|---|
| apis | 必要な API の有効化。既定の Compute SA に Editor があれば警告(`REMOVE_DEFAULT_EDITOR=1` で外す) | 5 |
| runtime | app 用の SA(app-runtime)、secret 2つ、片方だけを読める権限 | 5 |
| app | ソースからデプロイ(ビルドは専用の app-builder)、ベースイメージの自動更新、認証必須 | 1・2 |
| registry | Artifact Registry(push 時に脆弱性スキャン)、古いイメージの自動削除 | 1・2 |
| patch | Cloud Scheduler → Cloud Build の週次再ビルド・再デプロイ(鍵なし)。api は権限なしの SA(api-runtime)で動かす。週次ビルドの SA(patch-runner)は、プロジェクトにはビルドの作成とログの書き込みだけ、ほかは対象ごとに付ける。初回は1回動かして api を作る | 1・2・5 |
| data | 個人データのバケット(公開防止、均一なアクセス、論理削除7日、30日で自動削除) | 6 |
| backup | バックアップ用のバケット(保持ポリシー、論理削除7日)。`BACKUP_PROJECT` が未指定か本番と同じなら作らない。`LOCK_BACKUP=1` でロック(元に戻せない。`BACKUP_RETENTION` の明示が必須) | 4・8 |
| detect | 監査ログからのアラート3つ(鍵の作成、allUsers の付与(Cloud Run・プロジェクト・Cloud Storage)、Cloud Run の IAM チェックの無効化。週次の再デプロイは除く)。同じ名前があれば中身を更新。通知先は Pub/Sub | 検知 |
| wif | GitHub Actions 用の WIF。条件でリポジトリと main ブランチに限定 | 3 |
| armor | Compute の API を有効にし、api をロードバランサ＋Cloud Armor(IP ごとに60秒30回)の後ろへ。run.app からは直接届かない | 9 |

保持ポリシーのロックは取り消せません。ロックしたバケットは保持期間が過ぎるまで消せず、プロジェクトにも削除防止の lien が付きます。試すときは `BACKUP_RETENTION=600s` のように短くしてください。

アラートの通知先は Pub/Sub だけです。人に届くよう、メールなどの通知チャネルをポリシーに足してください。自分の CI の SA が LB の後ろのサービスを再デプロイするなら、`ALERT_EXCLUDE_SA="<SA のメールアドレス> ..."` を付けて `detect` を流すと、その SA が直接動いた操作をアラートから除きます(人がその SA になりすました操作は除きません)。`armor` を流し直すと、オーナーの手で IAM チェックを外す操作になるので、アラートが鳴ります(想定どおり)。

ロードバランサは検証のため HTTP(80) です。本番ではドメインと証明書を用意して HTTPS で公開してください。
