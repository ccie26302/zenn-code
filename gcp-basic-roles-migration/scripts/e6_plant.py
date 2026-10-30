#!/usr/bin/env python3
"""E6: 評価用のプロジェクトに、乱数でバケットとデータセットを植える。
植えた設定は data/e6_plant_<seed>.json に保存し、中身は表示しない(ハッシュだけ表示)。
使い方: python3 e6_plant.py <PROJECT> <SEED>"""
import hashlib, json, random, subprocess, sys, pathlib
P, SEED = sys.argv[1], int(sys.argv[2])
TAG = sys.argv[3] if len(sys.argv) > 3 else "b"
ROOT = pathlib.Path(__file__).resolve().parent.parent
rng = random.Random(SEED)
PN = subprocess.check_output(["gcloud", "projects", "describe", P, "--format=value(projectNumber)"]).decode().strip()
ME = subprocess.check_output(["gcloud", "config", "get", "account"], stderr=subprocess.DEVNULL).decode().strip()
def sh(*a):
    return subprocess.run(list(a), capture_output=True, text=True)
TEAMS = {"owners": ("projectOwner", "roles/storage.legacyBucketOwner"), "editors": ("projectEditor", "roles/storage.legacyBucketOwner"),
         "viewers": ("projectViewer", "roles/storage.legacyBucketReader")}
plan = {"seed": SEED, "buckets": [], "datasets": []}
open("/tmp/e6_obj.txt", "w").write("x\n")
for i in range(12):
    name = f"{P}-{TAG}{i:02d}"
    ubla = rng.random() < 0.4
    remove = [t for t in TEAMS if rng.random() < 0.5]
    decoy = rng.random() < 0.3
    b = {"name": name, "ubla": ubla, "remove_teams": remove, "decoy_label": decoy, "objects": []}
    args = ["gcloud", "storage", "buckets", "create", f"gs://{name}", f"--project={P}", "--location=asia-northeast1"]
    if ubla: args.append("--uniform-bucket-level-access")
    sh(*args)
    if decoy:
        sh("gcloud", "storage", "buckets", "update", f"gs://{name}", "--update-labels=restricted=true")
    for j in range(3):
        sh("gcloud", "storage", "cp", "/tmp/e6_obj.txt", f"gs://{name}/o{j}.txt", "--quiet")
    if not ubla:
        # 自分を ACL に足してから、指定のチームを外す
        sh("gcloud", "storage", "buckets", "update", f"gs://{name}", f"--add-acl-grant=entity=user-{ME},role=OWNER", f"--add-default-object-acl-grant=entity=user-{ME},role=OWNER")
        for t in remove:
            sh("gcloud", "storage", "buckets", "update", f"gs://{name}", f"--remove-acl-grant=project-{t}-{PN}", f"--remove-default-object-acl-grant=project-{t}-{PN}")
        for j in range(3):
            rm_obj = [t for t in TEAMS if rng.random() < 0.3]
            for t in rm_obj:
                sh("gcloud", "storage", "objects", "update", f"gs://{name}/o{j}.txt", f"--remove-acl-grant=project-{t}-{PN}")
            b["objects"].append({"name": f"o{j}.txt", "remove_teams": rm_obj})
    else:
        sh("gcloud", "storage", "buckets", "add-iam-policy-binding", f"gs://{name}", f"--member=user:{ME}", "--role=roles/storage.admin", "--format=none")
        pol = json.loads(sh("gcloud", "storage", "buckets", "get-iam-policy", f"gs://{name}", "--format=json").stdout)
        drop = {f"{TEAMS[t][0]}:{P}" for t in remove}
        for x in pol["bindings"]:
            x["members"] = [m for m in x["members"] if m not in drop]
        pol["bindings"] = [x for x in pol["bindings"] if x["members"]]
        open("/tmp/e6_pol.json", "w").write(json.dumps(pol))
        sh("gcloud", "storage", "buckets", "set-iam-policy", f"gs://{name}", "/tmp/e6_pol.json", "--format=none")
        b["objects"] = [{"name": f"o{j}.txt", "remove_teams": []} for j in range(3)]
    plan["buckets"].append(b)
SG = {"owners": "projectOwners", "editors": "projectWriters", "viewers": "projectReaders"}
for i in range(8):
    d = f"e6{TAG}_d{i:02d}"
    remove = [t for t in SG if rng.random() < 0.5]
    decoy = rng.random() < 0.3
    sh("bq", f"--project_id={P}", "mk", "--dataset", f"{P}:{d}")
    sh("bq", f"--project_id={P}", "query", "--use_legacy_sql=false", "--quiet", f"CREATE OR REPLACE TABLE `{P}.{d}.t1` AS SELECT 1 AS id")
    ds = json.loads(sh("bq", f"--project_id={P}", "show", "--format=prettyjson", f"{P}:{d}").stdout)
    ds["access"] = [e for e in ds["access"] if e.get("specialGroup") not in {SG[t] for t in remove}]
    if decoy:
        ds["description"] = "restricted"
    open("/tmp/e6_ds.json", "w").write(json.dumps(ds))
    sh("bq", f"--project_id={P}", "update", "--source", "/tmp/e6_ds.json", f"{P}:{d}")
    plan["datasets"].append({"name": d, "remove_teams": remove, "decoy": decoy})
out = ROOT / "data" / f"e6_plant_{TAG}_{SEED}.json"
s = json.dumps(plan, sort_keys=True)
out.write_text(s)
print("planted; sha256 =", hashlib.sha256(s.encode()).hexdigest())
