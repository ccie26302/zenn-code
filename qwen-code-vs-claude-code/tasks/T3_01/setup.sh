set -e; . /tasks/tfsetup.sh
python3 -c "import sys; sys.path.insert(0,'/tasks/T3_01'); sys.path.insert(0,'/tasks'); from files import FILES; from tfwrite import write; write('/work/infra', FILES)"
tf_apply
gcloud storage buckets update gs://qg-$ID-drift --update-labels=env=test --remove-labels=team -q >/dev/null
record qg-$ID-drift
