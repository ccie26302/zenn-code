"""共通: トークンの取得、REST の呼び出し、結果の分類"""
import json, pathlib, subprocess, time, urllib.request, urllib.error, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
P = (ROOT / "project.txt").read_text().strip()
PN = (ROOT / "project_number.txt").read_text().strip()
PRINCIPALS = ["none", "viewer", "reader", "editor", "writer", "owner", "admin"]

def sa_email(role):
    return f"br-{role}@{P}.iam.gserviceaccount.com"

_user_tok = {"t": None, "at": 0}
def user_token(force=False):
    if force or time.time() - _user_tok["at"] > 1800 or not _user_tok["t"]:
        for _ in range(5):
            t = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True).stdout.strip()
            if t.startswith("ya29."):
                _user_tok["t"] = t; _user_tok["at"] = time.time(); break
            time.sleep(3)
    return _user_tok["t"]

_sa_tok = {}
def token(principal):
    """principal: 'me' か PRINCIPALS のどれか。SA はなりすましで 1 時間のトークンを取る(45 分で更新)"""
    if principal == "me":
        return user_token()
    t = _sa_tok.get(principal)
    if t and time.time() - t[1] < 2700:
        return t[0]
    st, body, _ = call("POST", f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{sa_email(principal)}:generateAccessToken",
                       user_token(), {"scope": ["https://www.googleapis.com/auth/cloud-platform"], "lifetime": "3600s"})
    if st != 200:
        raise RuntimeError(f"token {principal}: {st} {body[:200]}")
    _sa_tok[principal] = (json.loads(body)["accessToken"], time.time())
    return _sa_tok[principal][0]

def call(method, url, tok, body=None, headers=None, raw=None, timeout=60):
    """戻り値: (HTTP ステータス, 本文の文字列, サーバの Date ヘッダー)"""
    h = {"Authorization": f"Bearer {tok}"}
    data = None
    if raw is not None:
        data = raw; h["Content-Type"] = "text/plain"
    elif body is not None:
        data = json.dumps(body).encode(); h["Content-Type"] = "application/json"
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode(errors="replace"), r.headers.get("Date")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace"), e.headers.get("Date")
    except Exception as e:  # ネットワークの失敗は 0 として記録
        return 0, repr(e), None

DENY_RE = re.compile(r"permission|denied|does not have|forbidden|not authorized|PERMISSION_DENIED|IAM_PERMISSION_DENIED", re.I)

def classify(status, body):
    """success / denied / undetermined。読み戻しの確認は各操作の側で行う"""
    if 200 <= status < 300:
        return "success"
    if status == 403 and DENY_RE.search(body or ""):
        return "denied"
    return "undetermined"

def short(body, n=300):
    try:
        j = json.loads(body)
        e = j.get("error", j)
        if isinstance(e, dict):
            reason = ""
            for d in e.get("details", []) or []:
                if d.get("reason"):
                    reason = d["reason"]
            if not reason and e.get("errors"):
                reason = e["errors"][0].get("reason", "")
            return f"{e.get('status','')}|{reason}|{str(e.get('message',''))[:n]}"
    except Exception:
        pass
    return (body or "")[:n]
