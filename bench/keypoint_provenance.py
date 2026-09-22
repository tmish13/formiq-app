#!/usr/bin/env python3
"""Stage 0b GATE — do the dataset's keypoints match what we serve?

`bench/results/2026-09-19-v1-held-out-evaluation.md:126` records that the dataset
keypoints came from a different pose pass than the container's MediaPipe. Under
the definitional design the ENTIRE calibration is a landmark offset measured on
dataset keypoints, so if the two passes disagree the offset does not transfer and
the rule is mis-calibrated in production by exactly that disagreement.

So this measures BIAS, not just correlation. Specifically the Bland-Altman mean
difference on `(hip_y - knee_y)/S` -- the quantity the verdict is a sign test on.

Three things are reported, in increasing order of what actually matters:

  1. per-indicator Pearson r          (does the shape survive?)
  2. Bland-Altman bias and limits     (does the ZERO survive? <- the verdict is a
                                       sign test, so a bias shifts every call)
  3. verdict agreement at the bottom  (how often does the definitional call flip?)

Run inside the container (needs MediaPipe + the app):

    docker run --rm --network deployment_default \
      -v $PWD/backend:/app -v $PWD:/repo \
      -v "$HOME/Desktop/Squat More/Labeled_Dataset/videos:/videos:ro" \
      -v "$HOME/Desktop/Squat More/Labeled_Dataset/processed_videos/keypoints:/keypoints:ro" \
      -v "$HOME/FORMIQ Form Analysis Model/data/squat_processed:/splits:ro" \
      -e POSTGRES_SERVER=db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
      -e POSTGRES_DB=formiq -e SECRET_KEY=dev-only-insecure-secret-key-32chars-minimum \
      -e REDIS_HOST=redis -e REDIS_PORT=6379 -w /app deployment-worker:latest \
      python /repo/bench/keypoint_provenance.py --n 30
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, "/app")

VIDEOS = Path("/videos")
KEYPOINTS = Path("/keypoints")
SPLITS = Path("/splits/user_level_multilabel_splits.json")
OUT = Path("/repo/bench/results/keypoint_provenance.json")

MIN_VIS = 0.4
SMOOTH = 5  # frames, odd

# PER SIDE, not pooled. A side view -- the best view for judging depth -- always
# occludes one leg, so requiring all eight core landmarks rejects exactly the
# videos where depth is most measurable. Measured on 32991_2: left side visibility
# 0.93-1.00, right knee 0.198, right ankle 0.225. Same shape mirrored on 33499_1.
# geometry.compute_knee_angles already gates per side; this matches it.
SIDES = {
    "L": {"shoulder": 11, "hip": 23, "knee": 25, "ankle": 27},
    "R": {"shoulder": 12, "hip": 24, "knee": 26, "ankle": 28},
}


# ------------------------------------------------------------------ geometry
def _angle(a, b, c):
    v1 = (a["x"] - b["x"], a["y"] - b["y"])
    v2 = (c["x"] - b["x"], c["y"] - b["y"])
    n1, n2 = math.hypot(*v1), math.hypot(*v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return None
    cos = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
    return math.degrees(math.acos(cos))


def usable_sides(lm):
    """Which sides have all four of their landmarks visible enough."""
    if lm is None or len(lm) < 33:
        return []
    out = []
    for name, idx in SIDES.items():
        if all(
            lm[i] is not None and (lm[i].get("visibility", 1.0) or 0.0) >= MIN_VIS
            for i in idx.values()
        ):
            out.append(name)
    return out


def hip_y(lm):
    """Mean hip y over usable sides."""
    sides = usable_sides(lm)
    if not sides:
        return None
    return st.mean(lm[SIDES[s]["hip"]]["y"] for s in sides)


def _torso(lm, s):
    idx = SIDES[s]
    sh, hp = lm[idx["shoulder"]], lm[idx["hip"]]
    return math.hypot(sh["x"] - hp["x"], sh["y"] - hp["y"])


def scale_ref(frames):
    """Median standing torso length over usable sides. Standing = lowest decile of hip_y."""
    ys = [(i, hip_y(f)) for i, f in enumerate(frames)]
    ys = [(i, y) for i, y in ys if y is not None]
    if len(ys) < 5:
        return None
    ordered = sorted(ys, key=lambda t: t[1])
    k = max(1, len(ordered) // 10)
    torsos = []
    for i, _ in ordered[:k]:
        lm = frames[i]
        for s in usable_sides(lm):
            t = _torso(lm, s)
            if t > 1e-6:
                torsos.append(t)
    return st.median(torsos) if torsos else None


def indicators(lm, S):
    """The four indicators, averaged over usable sides. I2 carries the verdict."""
    sides = usable_sides(lm)
    if not sides or not S:
        return None
    i1s, i2s, i3s, i4s = [], [], [], []
    for s in sides:
        idx = SIDES[s]
        hp, kn, an, sh = lm[idx["hip"]], lm[idx["knee"]], lm[idx["ankle"]], lm[idx["shoulder"]]
        femur = math.hypot(kn["x"] - hp["x"], kn["y"] - hp["y"])
        if femur > 1e-9:
            i1s.append(math.degrees(math.asin(
                max(-1.0, min(1.0, (kn["y"] - hp["y"]) / femur)))))
        i2s.append((hp["y"] - kn["y"]) / S)
        a = _angle(hp, kn, an)
        if a is not None:
            i3s.append(a)
        a = _angle(sh, hp, kn)
        if a is not None:
            i4s.append(a)
    return {
        "I1_femur_incline": st.mean(i1s) if i1s else None,
        "I2_hip_knee_delta": st.mean(i2s) if i2s else None,
        "I3_knee_flexion": st.mean(i3s) if i3s else None,
        "I4_hip_flexion": st.mean(i4s) if i4s else None,
    }


def smooth(vals, k=SMOOTH):
    n = len(vals)
    if n < k:
        return list(vals)
    half = k // 2
    out = []
    for i in range(n):
        lo, hi = max(0, i - half), min(n, i + half + 1)
        w = [v for v in vals[lo:hi] if v is not None]
        out.append(st.mean(w) if w else None)
    return out


def find_bottom(frames):
    """argmax(smoothed hip_y). One rep per video -- confirmed, so one bottom."""
    ys = [hip_y(f) for f in frames]
    sm = smooth(ys)
    best, bi = None, None
    for i, v in enumerate(sm):
        if v is not None and (best is None or v > best):
            best, bi = v, i
    return bi


# ------------------------------------------------------------------- stats --
def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = st.mean(xs), st.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = math.sqrt(sum((a - mx) ** 2 for a in xs))
    dy = math.sqrt(sum((b - my) ** 2 for b in ys))
    return num / (dx * dy) if dx > 1e-12 and dy > 1e-12 else float("nan")


def bland_altman(xs, ys):
    """(bias, sd, lo, hi) for ys - xs. Bias is what adds to the fitted offset."""
    d = [b - a for a, b in zip(xs, ys)]
    if len(d) < 3:
        return float("nan"), float("nan"), float("nan"), float("nan")
    bias, sd = st.mean(d), st.pstdev(d)
    return bias, sd, bias - 1.96 * sd, bias + 1.96 * sd


# -------------------------------------------------------------------- main --
def pick_videos(n):
    sp = json.loads(SPLITS.read_text())
    by_class = {}
    for split in ("train", "validation", "test"):
        for r in sp["splits"][split]["video_data"]:
            cls = (r.get("enhanced_labels", {}).get("video_level", {}) or {}).get("class_label")
            name = r["video_name"]
            if not cls:
                continue
            if not (VIDEOS / f"{name}.mp4").exists():
                continue
            if not (KEYPOINTS / f"{name}_keypoints.json").exists():
                continue
            by_class.setdefault(cls, []).append(name)
    picked, per = [], max(1, n // max(1, len(by_class)))
    for cls in sorted(by_class):
        picked += sorted(by_class[cls])[:per]
    return picked[:n]


def extract_live(path, ai, settings):
    from app.tasks.analysis_tasks import _extract_pose_from_video
    pose, _n, fps = asyncio.run(_extract_pose_from_video(str(path), ai, settings))
    return pose, fps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    args = ap.parse_args()

    from app.core.config import get_settings
    from app.services.ai_service import AIService

    settings = get_settings()
    ai = AIService(app_settings=settings)
    print(f"MediaPipe complexity in use: {ai._pose_complexity_used} "
          f"(fallback={ai._pose_complexity_fallback})")

    names = pick_videos(args.n)
    print(f"videos selected: {len(names)}")

    paired = {k: ([], []) for k in ("I1_femur_incline", "I2_hip_knee_delta",
                                    "I3_knee_flexion", "I4_hip_flexion")}
    bottom_delta, verdict_rows, per_video = [], [], []

    for idx, name in enumerate(names, 1):
        ds = json.loads((KEYPOINTS / f"{name}_keypoints.json").read_text())
        ds_frames = [f["landmarks"] for f in ds]
        live_frames, _fps = extract_live(VIDEOS / f"{name}.mp4", ai, settings)

        S_ds, S_live = scale_ref(ds_frames), scale_ref(live_frames)
        if not S_ds or not S_live:
            print(f"  [{idx:2d}/{len(names)}] {name}: no scale ref, skipped")
            continue

        n_common = min(len(ds_frames), len(live_frames))
        matched = 0
        for i in range(n_common):
            a = indicators(ds_frames[i], S_ds)
            b = indicators(live_frames[i], S_live)
            if a is None or b is None:
                continue
            ok = True
            for k in paired:
                if a[k] is None or b[k] is None:
                    ok = False
            if not ok:
                continue
            for k in paired:
                paired[k][0].append(a[k])
                paired[k][1].append(b[k])
            matched += 1

        bd, bl = find_bottom(ds_frames), find_bottom(live_frames)
        if bd is not None and bl is not None:
            bottom_delta.append(abs(bd - bl))
            va = indicators(ds_frames[bd], S_ds)
            vb = indicators(live_frames[bl], S_live)
            if va and vb and va["I2_hip_knee_delta"] is not None and vb["I2_hip_knee_delta"] is not None:
                verdict_rows.append((va["I2_hip_knee_delta"] >= 0,
                                     vb["I2_hip_knee_delta"] >= 0,
                                     va["I2_hip_knee_delta"], vb["I2_hip_knee_delta"]))

        per_video.append({"video": name, "frames_ds": len(ds_frames),
                          "frames_live": len(live_frames), "matched": matched,
                          "S_ds": S_ds, "S_live": S_live,
                          "bottom_ds": bd, "bottom_live": bl})
        print(f"  [{idx:2d}/{len(names)}] {name}: ds={len(ds_frames)} live={len(live_frames)} "
              f"matched={matched} bottom {bd}->{bl}")

    # ---------------------------------------------------------------- report
    print()
    print("=" * 74)
    print("1. CORRELATION — does the shape survive the pose pass?")
    print("=" * 74)
    results = {}
    for k, (xs, ys) in paired.items():
        r = pearson(xs, ys)
        results[k] = {"n": len(xs), "pearson_r": r}
        flag = "PASS" if r >= 0.90 else "**FAIL**"
        print(f"  {k:20s} n={len(xs):6d}  r={r:+.4f}   {flag}")

    print()
    print("=" * 74)
    print("2. BLAND-ALTMAN BIAS — does the ZERO survive?  [the one that matters]")
    print("=" * 74)
    print("  The verdict is sign(I2), so a bias shifts EVERY call by that amount.")
    print()
    for k, (xs, ys) in paired.items():
        bias, sd, lo, hi = bland_altman(xs, ys)
        results[k].update({"bias_live_minus_ds": bias, "sd": sd, "loa": [lo, hi]})
        print(f"  {k:20s} bias={bias:+.4f}  sd={sd:.4f}  LoA=[{lo:+.4f}, {hi:+.4f}]")
    i2 = results["I2_hip_knee_delta"]
    print()
    print(f"  I2 bias in units of the verdict: {i2['bias_live_minus_ds']:+.4f} torso-lengths")
    print( "  => a fitted offset from dataset keypoints is wrong by this much at serving")

    print()
    print("=" * 74)
    print("3. VERDICT AGREEMENT at the bottom — how often does the call flip?")
    print("=" * 74)
    if verdict_rows:
        agree = sum(1 for a, b, _, _ in verdict_rows if a == b)
        print(f"  videos compared      : {len(verdict_rows)}")
        print(f"  definitional verdict agrees: {agree}/{len(verdict_rows)} "
              f"({agree / len(verdict_rows):.1%})")
        flips = [(va, vb) for a, b, va, vb in verdict_rows if a != b]
        if flips:
            print(f"  flipped, |I2| at bottom (ds, live):")
            for va, vb in flips[:8]:
                print(f"    {va:+.4f}  ->  {vb:+.4f}")
        results["verdict_agreement"] = agree / len(verdict_rows)
        results["verdict_rows"] = [
            {"ds": va, "live": vb} for _, _, va, vb in verdict_rows
        ]

        # Does abstaining absorb the disagreement? A deadband m means "call it
        # only when |I2| > m". Report agreement among calls BOTH sources make
        # confidently, and the coverage that costs.
        print()
        print("  agreement among CONFIDENT calls, by deadband m on |I2|:")
        print(f"    {'m':>7s}  {'both confident':>15s}  {'coverage':>9s}  {'agree':>7s}")
        results["deadband_sweep"] = []
        for m in (0.0, 0.01, 0.02, 0.03, 0.05, 0.08, 0.10):
            conf = [(a, b) for _, _, a, b in verdict_rows
                    if abs(a) > m and abs(b) > m]
            if not conf:
                continue
            ag = sum(1 for a, b in conf if (a >= 0) == (b >= 0))
            cov = len(conf) / len(verdict_rows)
            print(f"    {m:7.2f}  {len(conf):15d}  {cov:8.1%}  {ag / len(conf):6.1%}")
            results["deadband_sweep"].append(
                {"m": m, "n": len(conf), "coverage": cov, "agreement": ag / len(conf)})
    if bottom_delta:
        print()
        print(f"  |bottom frame delta| : median={st.median(bottom_delta):.0f} "
              f"mean={st.mean(bottom_delta):.1f} max={max(bottom_delta)} frames")
        results["bottom_delta_median"] = st.median(bottom_delta)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"complexity": ai._pose_complexity_used, "indicators": results,
         "per_video": per_video}, indent=2))
    print()
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
