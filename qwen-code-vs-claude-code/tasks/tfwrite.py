# Terraform の課題の模範解答・初期状態の共通: .tf を書き出す
import os
PROV = '''terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "7.8.0" }
  }
}

provider "google" {
  region = "asia-northeast1"
}
'''
def write(d, files):
    os.makedirs(d, exist_ok=True)
    for n, t in files.items():
        p = os.path.join(d, n); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(t)
