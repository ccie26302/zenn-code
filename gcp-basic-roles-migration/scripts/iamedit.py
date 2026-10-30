"""プロジェクトの IAM ポリシーを、自分の権限で読み書きする(etag 付きで競合を避ける)"""
import json, time
from brlib import P, call, user_token

CRM = f"https://cloudresourcemanager.googleapis.com/v1/projects/{P}"
H = {"x-goog-user-project": P}

def get():
    st, body, _ = call("POST", f"{CRM}:getIamPolicy", user_token(), {"options": {"requestedPolicyVersion": 3}}, headers=H)
    if st == 401:
        st, body, _ = call("POST", f"{CRM}:getIamPolicy", user_token(force=True), {"options": {"requestedPolicyVersion": 3}}, headers=H)
    assert st == 200, body
    pol = json.loads(body); pol["version"] = 3
    return pol

def _set(pol):
    st, body, date = call("POST", f"{CRM}:setIamPolicy", user_token(), {"policy": pol}, headers=H)
    if st == 401:
        st, body, date = call("POST", f"{CRM}:setIamPolicy", user_token(force=True), {"policy": pol}, headers=H)
    return st, body, date

def modify(fn, retries=5):
    """fn(bindings) -> 新しい bindings。戻り値: (送った時刻 time.time(), 応答の Date)"""
    for _ in range(retries):
        pol = get()
        pol["bindings"] = fn(pol.get("bindings", []))
        t = time.time()
        st, body, date = _set(pol)
        if st == 200:
            return t, date
        if st == 409 or "etag" in body.lower():
            time.sleep(1); continue
        raise RuntimeError(f"setIamPolicy {st} {body[:300]}")
    raise RuntimeError("setIamPolicy: too many conflicts")

def add(member, role, condition=None):
    def fn(bs):
        b = {"role": role, "members": [member]}
        if condition:
            b["condition"] = condition
        return bs + [b]
    return modify(fn)

def remove(member, role):
    def fn(bs):
        out = []
        for b in bs:
            if b["role"] == role and member in b["members"]:
                ms = [m for m in b["members"] if m != member]
                if ms:
                    b = dict(b, members=ms)
                else:
                    continue
            out.append(b)
        return out
    return modify(fn)

def replace(member, old_role, new_role):
    def fn(bs):
        out = []
        for b in bs:
            if b["role"] == old_role and member in b["members"]:
                ms = [m for m in b["members"] if m != member]
                if ms:
                    out.append(dict(b, members=ms))
                continue
            out.append(b)
        return out + [{"role": new_role, "members": [member]}]
    return modify(fn)
