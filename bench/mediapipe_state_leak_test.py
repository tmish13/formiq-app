#!/usr/bin/env python3
"""
Does a video's prob_fault depend on which video the worker processed BEFORE it?

AIService is a per-worker singleton holding one mp.solutions.pose.Pose with
static_image_mode=False, i.e. a stateful tracker. If state survives across videos,
identical bytes produce different scores depending on the predecessor.
"""
import sys
from pathlib import Path
sys.path.insert(0, "/app")
VID = Path("/videos")
TARGET, OTHERS = "33387_1", ["33348_2", "36049_2"]

def main():
    import cv2
    from app.core.config import get_settings
    from app.services.ai_service import AIService
    from app.ml.posture_v1.loader import PostureV1TorchLoader
    s = get_settings(); loader = PostureV1TorchLoader(s); loader._ensure_loaded()
    def run(ai, vid):
        cap = cv2.VideoCapture(str(VID / f"{vid}.mp4")); pose = []
        while cap.isOpened() and len(pose) < 300:
            ok, fr = cap.read()
            if not ok: break
            lm, _ = ai.detect_pose(fr); pose.append(lm if lm else None)
        cap.release(); return loader.predict_posture(pose)["prob_fault"]
    cold1 = run(AIService(app_settings=s), TARGET)
    cold2 = run(AIService(app_settings=s), TARGET)
    print(f"cold tracker, run 1            : {cold1:.6f}")
    print(f"cold tracker, run 2            : {cold2:.6f}   (deterministic when cold: {abs(cold1-cold2) < 1e-9})")
    for prev in OTHERS:
        ai = AIService(app_settings=s); run(ai, prev)
        warm = run(ai, TARGET)
        print(f"same video after {prev:9s}      : {warm:.6f}   shift vs cold {warm-cold1:+.6f}")
    ai = AIService(app_settings=s); run(ai, TARGET)
    print(f"same video after ITSELF        : {run(ai, TARGET):.6f}")

if __name__ == "__main__":
    main()
