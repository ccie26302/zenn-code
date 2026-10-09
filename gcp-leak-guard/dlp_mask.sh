#!/bin/bash
# LLM に渡す前に、プロンプトの個人情報を Sensitive Data Protection(DLP)で伏せる。
# usage: PROJECT_ID=xxx ./dlp_mask.sh < prompt.txt   (文章は標準入力から読む。引数で渡すとシェルの履歴とプロセス一覧に残るため。CUSTOM=0 で customInfoType なしと比べられる。処理は既定で東京リージョン: DLP_LOCATION)
set -euo pipefail
: "${PROJECT_ID:?}"; TEXT=$(cat); [ -n "$TEXT" ] || { echo "標準入力から文章を渡してください" >&2; exit 1; }; CUSTOM=${CUSTOM:-1}
# リクエストは一時ファイルに書かず、パイプで渡す(個人情報を平文でディスクに残さない)
REQ=$(DLP_TEXT="$TEXT" python3 - "$CUSTOM" <<'PY'   # 文章は引数ではなく環境変数で渡す(プロセス一覧に出さない)
import json, os, sys
text, custom = os.environ["DLP_TEXT"], sys.argv[1] == "1"
info_types = [{"name": n} for n in ["PERSON_NAME", "EMAIL_ADDRESS", "PHONE_NUMBER", "JAPAN_INDIVIDUAL_NUMBER", "CREDIT_CARD_NUMBER"]]
cfg = {"infoTypes": info_types, "minLikelihood": "POSSIBLE"}
if custom:
    # 日本の携帯番号は文脈で確信度が下がり、しきい値だけだと取りこぼす。正規表現で名指しして拾う
    cfg["customInfoTypes"] = [{"infoType": {"name": "JP_MOBILE"}, "regex": {"pattern": r"0[789]0-?\d{4}-?\d{4}"}, "likelihood": "VERY_LIKELY"}]
print(json.dumps({
  "item": {"value": text}, "inspectConfig": cfg,
  "deidentifyConfig": {"infoTypeTransformations": {"transformations": [{"primitiveTransformation": {"replaceWithInfoTypeConfig": {}}}]}}
}, ensure_ascii=False))
PY
)
printf '%s' "$REQ" | curl -s -X POST "https://dlp.googleapis.com/v2/projects/$PROJECT_ID/locations/${DLP_LOCATION:-asia-northeast1}/content:deidentify" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "x-goog-user-project: $PROJECT_ID" \
  -H "Content-Type: application/json" --data-binary @- | python3 -c "import json,sys;print(json.load(sys.stdin)['item']['value'])"
