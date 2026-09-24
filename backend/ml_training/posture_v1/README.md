# ml_training/posture_v1

The seeded trainer for PostureV1 (plan Track B5): the notebook's recipe, the serving code, one
logged test read. Three modules, each a `python -m` entry point run inside the worker image (torch):

```bash
IMG="docker run --rm -m 6g --network deployment_default -v $PWD/backend:/app -v $PWD:/repo \
     -e SECRET_KEY=dev-only-insecure-secret-key-32chars-minimum -w /app deployment-worker:latest"

# 1. arrays from the SERVING pose pass (bench/cache/keypoints_live) and the content-level splits
$IMG python -m ml_training.posture_v1.dataset \
     --splits /repo/bench/results/content_level_splits.json \
     --ml-splits ml_training/data/user_level_multilabel_splits.json \
     --cache /repo/bench/cache/keypoints_live --out /repo/bench/cache/trainer_port/data --target posture_collapsed

# 2. five seeds on train/validation; the artifact is the median-validation-AUROC seed
$IMG python -m ml_training.posture_v1.train --data /repo/bench/cache/trainer_port/data --out /repo/bench/cache/trainer_port/run --seeds 0 1 2 3 4

# 3. the artifact triple with a full provenance block (never the live directory without --install)
$IMG python -m ml_training.posture_v1.export --run /repo/bench/cache/trainer_port/run --seed <selected> \
     --data-manifest /repo/bench/cache/trainer_port/data/manifest.json --out /repo/bench/cache/trainer_port/artifacts

# 4. the ONE test read for that artifact, appended to TEST_READ_LOG.jsonl; a second is refused
$IMG python -m ml_training.posture_v1.train --data /repo/bench/cache/trainer_port/data --out /repo/bench/cache/trainer_port/run \
     --reports /repo/bench/results/retrain --final
```

What is reused from serving, so parity is by construction: `PostureV1Model` built from the shipped
manifest's `model_config`, `preprocess_pose_data`, `compute_151d_features`, `app/eval/metrics.py`.
What the notebook did not do: seeds everywhere, a deep copy of the best state, and the test split
never opened by training. `tests/unit/test_trainer_port.py` holds the architecture-parity check
against the shipped checkpoint, a synthetic smoke train → export → serving-loader round trip, the
deep-copy check and the final-read guard.

A model trained on the CURRENT labels is not a candidate: the acceptance bar's stop rule counts it
as the second failed intervention. The trainer exists so that the relabelling pilot's labels, if the
gates pass, can be trained on with one command and one read.
