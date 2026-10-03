"""kev-4b の CUDA コンテナを Vertex AI エンドポイント(専用エンドポイント)にデプロイ/撤去する。

usage:
  uv run --with google-cloud-aiplatform cloud/gpu_endpoint.py deploy <tag> <region> <machine> <accel>
      例: deploy l4-tokyo asia-northeast1 g2-standard-8 NVIDIA_L4
          deploy l4-us    us-central1     g2-standard-8 NVIDIA_L4
          deploy rtx-us   us-central1     g4-standard-48 NVIDIA_RTX_PRO_6000
  uv run --with google-cloud-aiplatform cloud/gpu_endpoint.py delete <tag>
  uv run --with google-cloud-aiplatform cloud/gpu_endpoint.py list

- 設計: 専用エンドポイント(dedicated_endpoint_enabled)=共有フロントを通らない低遅延経路。クラウドに最も有利な条件で比べる。
- min=max=1 レプリカ(オートスケールの揺れを入れない)。
- 状態は data/endpoints.json に保存(撤去漏れ防止)。
"""
import json, os, sys, time
from google.cloud import aiplatform

PROJECT = os.environ["PROJECT_ID"]  # 検証用プロジェクトを必ず明示する
IMAGE = os.environ.get("KEV_IMAGE", f"asia-northeast1-docker.pkg.dev/{PROJECT}/owata/kev-gpu:v2")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "data", "endpoints.json")
import fcntl


def load():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def save(d):
    # 3並列デプロイで同時書き込みし、記録が消えた。ロックして「読んで→自分の tag だけ更新」にする
    with open(STATE + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        cur = load()
        cur.update(d)
        json.dump(cur, open(STATE, "w"), indent=1)


def deploy(tag, region, machine, accel):
    aiplatform.init(project=PROJECT, location=region)
    st = load()
    t0 = time.time()
    model = aiplatform.Model.upload(
        display_name=f"kev4b-{tag}", serving_container_image_uri=IMAGE,
        serving_container_predict_route="/v1/systemone",
        # kev.serve に /health は無い(404)。/health を指定して1回デプロイを失敗させた → /v1/models(200を確認済み)
        serving_container_health_route="/v1/models", serving_container_ports=[8080],
        # python:slim ベースでは GPU ドライバ(Vertex が /usr/local/nvidia に差し込む)が見えず、kev が黙って CPU で起動した。
        # NVIDIA 公式イメージと同じ環境変数を渡して見えるようにする。
        serving_container_environment_variables={
            "LD_LIBRARY_PATH": "/usr/local/nvidia/lib64:/usr/local/nvidia/lib",
            "NVIDIA_VISIBLE_DEVICES": "all", "NVIDIA_DRIVER_CAPABILITIES": "compute,utility",
            "PATH": "/usr/local/nvidia/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"})
    ep = aiplatform.Endpoint.create(display_name=f"kev4b-{tag}", dedicated_endpoint_enabled=True)
    st[tag] = dict(region=region, machine=machine, accel=accel, model=model.resource_name,
                   endpoint=ep.resource_name, status="deploying", t_start=t0)
    save(st)
    # 注意: ヘルスチェックが通らないとデプロイ操作は取り消し不可のまま最大約1.5時間ノード課金が続いた。
    # SDK からサーバ側の待ち時間は設定できないので、ヘルス経路は事前にローカルの同一コードで 200 を確認すること。
    model.deploy(endpoint=ep, machine_type=machine, accelerator_type=accel, accelerator_count=1,
                 min_replica_count=1, max_replica_count=1, deploy_request_timeout=3600)
    ep = aiplatform.Endpoint(ep.resource_name)
    dns = ep.gca_resource.dedicated_endpoint_dns
    st = load()
    st[tag].update(status="ready", dns=dns, t_ready=time.time(),
                   deploy_min=round((time.time() - t0) / 60, 1))
    save(st)
    print(json.dumps(st[tag], indent=1))


def delete(tag):
    st = load(); e = st[tag]
    aiplatform.init(project=PROJECT, location=e["region"])
    ep = aiplatform.Endpoint(e["endpoint"])
    ep.undeploy_all(); ep.delete()
    aiplatform.Model(e["model"]).delete()
    e.update(status="deleted", t_deleted=time.time(),
             billed_hours=round((time.time() - e["t_start"]) / 3600, 2))
    save(st); print(tag, "deleted", e["billed_hours"], "h")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "deploy": deploy(*sys.argv[2:6])
    elif cmd == "delete": delete(sys.argv[2])
    elif cmd == "list": print(json.dumps(load(), indent=1))
