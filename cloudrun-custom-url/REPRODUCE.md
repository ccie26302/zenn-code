# REPRODUCE

gcloud 587.0.0 以上(582.0.0 では cloud.run を自社ドメインとして扱い、所有確認を求めて止まる)。

```bash
export PROJECT_A=<プロジェクト A>; export PROJECT_B=<プロジェクト B>; R=asia-northeast1
for p in $PROJECT_A $PROJECT_B; do gcloud services enable run.googleapis.com --project $p; done
gcloud run deploy svc-alpha --image=us-docker.pkg.dev/cloudrun/container/hello --region=$R --project $PROJECT_A --allow-unauthenticated --max-instances=1
gcloud run deploy svc-bravo --image=us-docker.pkg.dev/cloudrun/container/hello --region=$R --project $PROJECT_B --allow-unauthenticated --max-instances=1

# 検証1・2: 削除と取得
N=<自分で考えた無害な名前>
gcloud beta run domain-mappings create --service=svc-alpha --domain=$N.cloud.run --region=$R --project $PROJECT_A
./measure_release.sh $N $PROJECT_A $PROJECT_B 1   # data/release.csv に記録
gcloud beta run domain-mappings create --service=svc-alpha --domain=$N.cloud.run --region=$R --project $PROJECT_A   # already exists
gcloud run deploy svc-alpha-us --image=us-docker.pkg.dev/cloudrun/container/hello --region=us-central1 --project $PROJECT_A --allow-unauthenticated --max-instances=1
gcloud beta run domain-mappings create --service=svc-alpha-us --domain=$N.cloud.run --region=us-central1 --project $PROJECT_A   # 別リージョンでも already exists

# 検証3: 外から閉じる(既定の URL の無効化)
gcloud beta run services update svc-bravo --no-default-url --region=$R --project $PROJECT_B

# 検証3: 外から閉じる(認証必須)
gcloud run deploy svc-private --image=us-docker.pkg.dev/cloudrun/container/hello --region=$R --project $PROJECT_A --no-allow-unauthenticated --max-instances=1
gcloud beta run domain-mappings create --service=svc-private --domain=<名前>.cloud.run --region=$R --project $PROJECT_A
curl -s -o /dev/null -w "%{http_code}\n" https://<名前>.cloud.run/
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $(gcloud auth print-identity-token)" https://<名前>.cloud.run/

# 検証3: 外から閉じる(ingress を internal に。ドキュメント上は非対応の構成)
gcloud run services update svc-bravo --ingress=internal --region=$R --project $PROJECT_B
```

## 防御側: 監査ログ

```bash
gcloud logging read 'logName:"cloudaudit.googleapis.com%2Factivity" AND protoPayload.methodName:"DomainMappings.DeleteDomainMapping"' --project $PROJECT_A --freshness=7d --format='value(timestamp,protoPayload.authenticationInfo.principalEmail,protoPayload.resourceName)'
```

後片付け: `gcloud beta run domain-mappings delete` は名前を手放すことになる点に注意(手放してよい名前だけ削除する)。
