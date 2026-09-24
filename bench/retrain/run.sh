#!/usr/bin/env bash
# Controlled retrain (ML_AUDIT §11c) -- every stage runs inside the freshly built image so the
# feature code, the serving loader and sklearn are the ones the deployment ships.
#
#   bash bench/retrain/run.sh extract   # serving-pass keypoints for every corpus video not yet cached
#   bash bench/retrain/run.sh build     # 3 arms x 3 splits -> bench/cache/retrain/data (+ manifest to results)
#   bash bench/retrain/run.sh valcheck  # incumbent on VALIDATION only (exercises the paired-comparison path)
#   bash bench/retrain/run.sh train     # 3 arms x 3 learners x 5 seeds, selection on validation only
#   bash bench/retrain/run.sh final     # ONE logged test read per (arm, learner), paired vs the incumbent
#
# Pickled models and .npz datasets go to bench/cache/retrain (gitignored, regenerable);
# JSON reports and TEST_READ_LOG.jsonl go to bench/results/retrain (committed).
# Env: MEM (container memory, default 3g), THREADS (BLAS/OpenMP threads, default 1 --
# HistGradientBoosting oversubscribes an 8-vCPU VM that is also running the worker).
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ML="${ML_REPO:-$HOME/FORMIQ Form Analysis Model}"
VIDS="${VID_DIR:-$HOME/Desktop/Squat More/Labeled_Dataset/videos}"
IMG="${IMG:-deployment-beat:latest}"
ARMS="A_v2_body B_temporal64 C_incumbent151"; MODELS="logreg hgb mlp"
DATA=/repo/bench/cache/retrain/data; ART=/repo/bench/cache/retrain/artifacts; REP=/repo/bench/results/retrain
run() {
  docker run --rm --network deployment_default -m "${MEM:-3g}" \
    -e OMP_NUM_THREADS="${THREADS:-1}" -e MKL_NUM_THREADS="${THREADS:-1}" -e OPENBLAS_NUM_THREADS="${THREADS:-1}" \
    -v "$REPO/backend:/app" -v "$REPO:/repo" -v "$ML/data/squat_processed:/splits:ro" -v "$VIDS:/videos:ro" -v "$ML:/ml:ro" \
    -e POSTGRES_SERVER=db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=formiq \
    -e SECRET_KEY=dev-only-insecure-secret-key-32chars-minimum -e REDIS_HOST=redis -e REDIS_PORT=6379 \
    -w /app "$IMG" "$@" 2>&1 | grep -v "Warning\|warn\|Loading environment\|CONFIG/\|PROGRESS_MODEL\|InconsistentVersion\|scikit-learn.org"
}
case "${1:-}" in
  extract)  run python -u /repo/bench/extract_keypoints.py --pass 2 --workers "${WORKERS:-4}" --min-free-gb 8 ;;
  build)    run python -u /repo/bench/retrain/build_dataset.py --splits /repo/bench/results/content_level_splits.json \
              --ml-splits /splits/user_level_multilabel_splits.json --cache /repo/bench/cache/keypoints_live \
              --out $DATA --reports $REP ;;
  valcheck) run python -u /repo/bench/retrain/incumbent_val_check.py $DATA /repo/bench/cache/keypoints_live $REP/incumbent_validation_check.json ;;
  train)    for arm in $ARMS; do for m in $MODELS; do echo "=== train $arm $m ==="
              run python -u /repo/bench/retrain/train.py --data $DATA --out $ART --reports $REP --arm $arm --model $m --seeds 0 1 2 3 4
            done; done ;;
  final)    for arm in $ARMS; do for m in $MODELS; do echo "=== FINAL $arm $m ==="
              run python -u /repo/bench/retrain/train.py --data $DATA --out $ART --reports $REP --arm $arm --model $m \
                --final --incumbent-cache /repo/bench/cache/keypoints_live
            done; done ;;
  *) echo "usage: $0 {extract|build|valcheck|train|final}"; exit 1 ;;
esac
