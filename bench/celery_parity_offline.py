#!/usr/bin/env python3
"""
Offline half of the Celery parity test: run the SAME raw .mp4 files through the same
decode -> MediaPipe -> preprocess -> features -> inference code, synchronously, with no
API, no Celery, no Postgres. Mirrors app/tasks/analysis_tasks.py::_extract_pose_from_video.
"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "/app")
VID = Path("/videos"); SEL = Path("/app_bench/parity_20_selection.json")

def main():
    import cv2
    from app.core.config import get_settings
    from app.services.ai_service import AIService
    from app.ml.posture_v1.loader import PostureV1TorchLoader
    s = get_settings(); ai = AIService(app_settings=s)
    loader = PostureV1TorchLoader(s); loader._ensure_loaded()
    max_frames = getattr(s, "AI_MAX_FRAMES_PER_VIDEO_ANALYSIS", 300) or 300
    out = []
    for r in json.loads(SEL.read_text()):
        cap = cv2.VideoCapture(str(VID / f"{r['video']}.mp4")); pose = []; n = 0
        while cap.isOpened() and n < max_frames:
            ok, frame = cap.read()
            if not ok: break
            lm, _ = ai.detect_pose(frame); pose.append(lm if lm else None); n += 1
        cap.release()
        res = loader.predict_posture(pose)
        out.append({"video": r["video"], "class": r["class"], "frames": n,
                    "prob_fault": res.get("prob_fault"), "decision": res.get("decision"),
                    "seq_len": (res.get("preprocessing") or {}).get("sequence_length")})
        print(r["video"], n, res.get("prob_fault"), res.get("decision"), flush=True)
    print("complexity", ai._pose_complexity_used, "fallback", ai._pose_complexity_fallback)
    print("===JSON==="); print(json.dumps(out))

if __name__ == "__main__":
    main()
