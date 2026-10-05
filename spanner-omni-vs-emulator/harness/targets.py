"""3つのターゲット(emu / omni / cloud)の Database を返す。DB 名は共通で cmp。"""
import os
from google.cloud import spanner
from google.auth.credentials import AnonymousCredentials

CLOUD_PROJECT, CLOUD_INSTANCE = os.environ.get("CLOUD_PROJECT", ""), os.environ.get("CLOUD_INSTANCE", "omni-truth")
EMU_HOST, OMNI_HOST = "localhost:9010", "localhost:15000"


def client(target):
    if target == "emu":
        os.environ["SPANNER_EMULATOR_HOST"] = EMU_HOST
        return spanner.Client(project="test-project", credentials=AnonymousCredentials())
    os.environ.pop("SPANNER_EMULATOR_HOST", None)
    if target == "omni":
        return spanner.Client(experimental_host=OMNI_HOST, use_plain_text=True)
    if target == "cloud":
        # ADC の quota_project は別プロジェクト(触らない約束)なので、検証用プロジェクトを明示して上書きする
        import google.auth
        creds, _ = google.auth.default(quota_project_id=CLOUD_PROJECT)
        return spanner.Client(project=CLOUD_PROJECT, credentials=creds, client_options={"quota_project_id": CLOUD_PROJECT})
    raise ValueError(target)


def instance(target):
    c = client(target)
    if target == "emu":
        inst = c.instance("test-instance")
        if not inst.exists():
            inst = c.instance("test-instance", configuration_name="projects/test-project/instanceConfigs/emulator-config",
                              node_count=1, display_name="test-instance")
            inst.create().result(120)
        return inst
    if target == "omni":
        return c.instance("default")
    return c.instance(CLOUD_INSTANCE)


def database(target, name="cmp", ddl=(), create=True):
    db = instance(target).database(name, ddl_statements=list(ddl))
    if create and not db.exists():
        db.create().result(600)
    return db
