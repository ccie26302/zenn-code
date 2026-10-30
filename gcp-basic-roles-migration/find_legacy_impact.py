#!/usr/bin/env python3
"""E6: 旧ロール(Owner/Editor/Viewer)→新ロール(Admin/Writer/Reader)の置き換えで、アクセスが変わる場所を洗い出す。
使い方: python3 e6_find.py <PROJECT_ID> [--json out.json]
必要な権限: プロジェクトの IAM の閲覧、バケットとデータセットの IAM/ACL の閲覧、ロール定義の取得
出力: 置き換え案、自動付与の SA、バケット/データセットごとの「広がる」「狭まる」権限"""
import argparse, json, subprocess, sys, urllib.request, urllib.error

PAIRS = {"owner": "admin", "editor": "writer", "viewer": "reader"}
# 簡易値と特殊グループは上位のロールを含む(E6 v1 の実測): Owner は editors/viewers にも、Editor は viewers にも数えられる
INCLUDES = {"owner": ["owner", "editor", "viewer"], "editor": ["editor", "viewer"], "viewer": ["viewer"]}
TEAM = {"owner": ("projectOwner", "owners", "projectOwners"),
        "editor": ("projectEditor", "editors", "projectWriters"),
        "viewer": ("projectViewer", "viewers", "projectReaders")}
# 確かめる権限(データに直接かかわるもの)
GCS_PERMS = ["storage.buckets.get", "storage.buckets.update", "storage.buckets.getIamPolicy", "storage.buckets.setIamPolicy",
             "storage.objects.list", "storage.objects.get", "storage.objects.create", "storage.objects.delete"]
BQ_PERMS = ["bigquery.tables.list", "bigquery.tables.get", "bigquery.tables.getData", "bigquery.tables.updateData",
            "bigquery.tables.create", "bigquery.tables.delete", "bigquery.datasets.update", "bigquery.datasets.setIamPolicy"]
# ACL の役割と、それに対応する IAM のロール(Cloud Storage と BigQuery のドキュメントの対応表)
BUCKET_ACL = {"READER": "roles/storage.legacyBucketReader", "WRITER": "roles/storage.legacyBucketWriter", "OWNER": "roles/storage.legacyBucketOwner"}
OBJECT_ACL = {"READER": "roles/storage.legacyObjectReader", "OWNER": "roles/storage.legacyObjectOwner"}
DATASET_ACL = {"READER": "roles/bigquery.dataViewer", "WRITER": "roles/bigquery.dataEditor", "OWNER": "roles/bigquery.dataOwner"}

_tok = None
def tok():
    global _tok
    if not _tok:
        _tok = subprocess.check_output(["gcloud", "auth", "print-access-token"], stderr=subprocess.DEVNULL).decode().strip()
    return _tok

def api(method, url, body=None, project=None):
    h = {"Authorization": f"Bearer {tok()}"}
    if project:
        h["x-goog-user-project"] = project
    data = None
    if body is not None:
        data = json.dumps(body).encode(); h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_body": e.read().decode(errors="replace")[:300]}

_roles = {}
def role_perms(role):
    """ロール定義を取る。定義が揺れることがある(E0)ので、3回取って和集合ではなく最頻を使う"""
    if role not in _roles:
        seen = {}
        for _ in range(3):
            j = api("GET", f"https://iam.googleapis.com/v1/{role}")
            s = frozenset(j.get("includedPermissions", []))
            seen[s] = seen.get(s, 0) + 1
        _roles[role] = set(max(seen, key=seen.get))
    return _roles[role]

def paged(url, key, project):
    out, tokn = [], None
    while True:
        u = url + (("&" if "?" in url else "?") + f"pageToken={tokn}" if tokn else "")
        j = api("GET", u, project=project)
        if "_error" in j:
            return out, j
        out += j.get(key, [])
        tokn = j.get("nextPageToken")
        if not tokn:
            return out, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--json")
    ap.add_argument("--max-objects", type=int, default=200, help="ACL を見るオブジェクトの上限(バケットごと)")
    a = ap.parse_args()
    P = a.project
    proj = api("GET", f"https://cloudresourcemanager.googleapis.com/v1/projects/{P}", project=P)
    PN = proj["projectNumber"]
    report = {"project": P, "bindings": [], "auto_grants": [], "buckets": [], "datasets": [], "errors": []}

    # 1. プロジェクトの IAM の旧ロール
    pol = api("POST", f"https://cloudresourcemanager.googleapis.com/v1/projects/{P}:getIamPolicy", {"options": {"requestedPolicyVersion": 3}}, project=P)
    auto = {f"serviceAccount:{PN}-compute@developer.gserviceaccount.com", f"serviceAccount:{P}@appspot.gserviceaccount.com",
            f"serviceAccount:{PN}@cloudservices.gserviceaccount.com"}
    for b in pol.get("bindings", []):
        r = b["role"].split("/")[-1]
        if r in PAIRS:
            for m in b["members"]:
                rec = {"member": m, "role": b["role"], "proposal": f"roles/{PAIRS[r]}"}
                (report["auto_grants"] if m in auto else report["bindings"]).append(rec)
    proj_perms = {r: role_perms(f"roles/{r}") for r in list(PAIRS) + list(PAIRS.values())}

    # 2. バケット
    buckets, err = paged(f"https://storage.googleapis.com/storage/v1/b?project={P}&projection=full", "items", P)
    if err:
        report["errors"].append({"buckets": err})
    for bk in buckets:
        name = bk["name"]
        ubla = bk.get("iamConfiguration", {}).get("uniformBucketLevelAccess", {}).get("enabled", False)
        iam = api("GET", f"https://storage.googleapis.com/storage/v1/b/{name}/iam?optionsRequestedPolicyVersion=3", project=P)
        objs = []
        if not ubla:
            items, _ = paged(f"https://storage.googleapis.com/storage/v1/b/{name}/o?projection=full&maxResults={a.max_objects}", "items", P)
            objs = items[: a.max_objects]
        for old, new in PAIRS.items():
            convs = [TEAM[x][0] for x in INCLUDES[old]]; teams = [TEAM[x][1] for x in INCLUDES[old]]
            legacy = set(proj_perms[old]); newp = set(proj_perms[new])
            # バケットの IAM で、簡易値(自分と下位のチーム)に付いているロール
            for b in iam.get("bindings", []):
                if any(f"{c}:{P}" in b.get("members", []) or f"{c}:{PN}" in b.get("members", []) for c in convs):
                    legacy |= role_perms(b["role"])
            # 細かいアクセス制御では、オブジェクトの読み取りはオブジェクトの ACL でも決まるので、下のオブジェクト単位で数える
            check = GCS_PERMS if ubla else [p for p in GCS_PERMS if p != "storage.objects.get"]
            gcs_old = {p for p in check if p in legacy}
            gcs_new = {p for p in check if p in newp}
            # オブジェクトの ACL(細かいアクセス制御のとき)。オブジェクト単位の差を数える
            obj_diff = {"widen_get": [], "narrow_get": []}
            for o in objs:
                ents = {x.get("entity") for x in o.get("acl", [])}
                old_get = ("storage.objects.get" in legacy) or any(f"project-{t}-{PN}" in ents for t in teams)
                new_get = "storage.objects.get" in newp
                if new_get and not old_get:
                    obj_diff["widen_get"].append(o["name"])
                if old_get and not new_get:
                    obj_diff["narrow_get"].append(o["name"])
            report["buckets"].append({"bucket": name, "ubla": ubla, "pair": f"{old}->{new}",
                                      "widen": sorted(gcs_new - gcs_old), "narrow": sorted(gcs_old - gcs_new),
                                      "objects_widen_get": len(obj_diff["widen_get"]), "objects_narrow_get": len(obj_diff["narrow_get"]),
                                      "objects_checked": len(objs), "objects_widen_list": obj_diff["widen_get"], "objects_narrow_list": obj_diff["narrow_get"]})

    # 3. データセット
    # all=true で隠しデータセット(_ で始まる、クエリ結果の置き場)も含める。表示では分けて扱う
    dss, err = paged(f"https://bigquery.googleapis.com/bigquery/v2/projects/{P}/datasets?all=true", "datasets", P)
    if err:
        report["errors"].append({"datasets": err})
    for d in dss:
        did = d["datasetReference"]["datasetId"]
        full = api("GET", f"https://bigquery.googleapis.com/bigquery/v2/projects/{P}/datasets/{did}", project=P)
        for old, new in PAIRS.items():
            sgs = [TEAM[x][2] for x in INCLUDES[old]]
            legacy = set(proj_perms[old]); newp = set(proj_perms[new])
            for e in full.get("access", []):
                if e.get("specialGroup") in sgs and e.get("role") in DATASET_ACL:
                    legacy |= role_perms(DATASET_ACL[e["role"]])
            o = {p for p in BQ_PERMS if p in legacy}; n = {p for p in BQ_PERMS if p in newp}
            report["datasets"].append({"dataset": did, "hidden": did.startswith("_"), "pair": f"{old}->{new}", "widen": sorted(n - o), "narrow": sorted(o - n)})

    if a.json:
        json.dump(report, open(a.json, "w"), ensure_ascii=False, indent=1)
    # 人が読む要約
    print(f"# {P}")
    print(f"旧ロールの付与: {len(report['bindings'])} 件(自動付与の SA {len(report['auto_grants'])} 件は別扱い)")
    for r in report["bindings"]:
        print(f"  {r['member']}  {r['role']} -> {r['proposal']}")
    for r in report["auto_grants"]:
        print(f"  [自動付与] {r['member']}  {r['role']}(置き換える前に、その SA が何に使われているかを確認)")
    for kind, key in [("バケット", "bucket"), ("データセット", "dataset")]:
        rows = [x for x in report[kind == "バケット" and "buckets" or "datasets"] if (x["widen"] or x["narrow"] or x.get("objects_widen_get") or x.get("objects_narrow_get")) and not x.get("hidden")]
        print(f"\n## {kind}: 差がある組 {len(rows)}")
        for x in rows:
            extra = ""
            if key == "bucket" and not x["ubla"]:
                extra = f"  オブジェクト(読み取り) 広がる {x['objects_widen_get']} / 狭まる {x['objects_narrow_get']} (調べた {x['objects_checked']})"
            print(f"  {x[key]}  {x['pair']}  広がる: {','.join(p.split('.',1)[1] for p in x['widen']) or '-'}  狭まる: {','.join(p.split('.',1)[1] for p in x['narrow']) or '-'}{extra}")
    hidden = sorted({x["dataset"] for x in report["datasets"] if x.get("hidden")})
    if hidden:
        print(f"\n隠しデータセット(クエリ結果の置き場) {len(hidden)} 個は上の数に含めていない")
    if report["errors"]:
        print("\nerrors:", report["errors"])

if __name__ == "__main__":
    main()
