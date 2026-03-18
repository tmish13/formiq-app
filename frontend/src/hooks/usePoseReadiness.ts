/**
 * usePoseReadiness
 *
 * Drives the camera readiness indicator using real in-browser pose detection
 * (MoveNet Lightning via @tensorflow-models/pose-detection).
 *
 * Detection is throttled to DETECTION_FPS and stops automatically when:
 *   • active === false (e.g. recording begins)
 *   • component unmounts
 *
 * All TFJS code is dynamically imported so the model only downloads the first
 * time the user opens the recording screen. Subsequent opens reuse the cached
 * detector instance.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { evaluateFramingReadiness } from '../utils/poseReadiness';

export type ReadinessState = 'initializing' | 'positioning' | 'ready';

/** Sampling rate during framing detection. 6 fps is plenty; keeps CPU low. */
const DETECTION_FPS = 6;
const INTERVAL_MS = Math.round(1000 / DETECTION_FPS);

// ── Module-level detector cache ──────────────────────────────────────────────
// The detector is expensive to load (~1–2 s first time). Cache it at module
// scope so it survives camera flips and navigate-back-to-page scenarios.
let _cachedDetector: {
  estimatePoses: (
    input: HTMLVideoElement,
  ) => Promise<Array<{ keypoints: Array<{ score?: number; y: number; x: number }> }>>;
  dispose?: () => void;
} | null = null;

let _loadPromise: Promise<void> | null = null;

async function ensureDetector(): Promise<void> {
  if (_cachedDetector) return;
  if (_loadPromise) return _loadPromise;

  _loadPromise = (async () => {
    const [poseDetection, , tf] = await Promise.all([
      import('@tensorflow-models/pose-detection'),
      import('@tensorflow/tfjs-backend-webgl'),
      import('@tensorflow/tfjs-core'),
    ]);

    await tf.ready();

    const detector = await poseDetection.createDetector(
      poseDetection.SupportedModels.MoveNet,
      {
        // Lightning = fastest / smallest model (~3 MB, 50+ FPS on modern mobile)
        modelType: (poseDetection as any).movenet?.modelType?.SINGLEPOSE_LIGHTNING
          ?? 'SinglePose.Lightning',
      },
    );

    _cachedDetector = detector;
  })();

  return _loadPromise;
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export interface UsePoseReadinessOptions {
  /** Ref to the <video> element streaming the camera feed. */
  videoRef: React.RefObject<HTMLVideoElement>;
  /**
   * When true the hook starts (or resumes) detection.
   * Pass false to pause detection (e.g. once recording starts).
   */
  active: boolean;
  /** Called exactly once each time the state transitions not-ready → ready. */
  onBecameReady: () => void;
}

export function usePoseReadiness({
  videoRef,
  active,
  onBecameReady,
}: UsePoseReadinessOptions): {
  readiness: ReadinessState;
  resetReadiness: () => void;
} {
  const [readiness, setReadiness] = useState<ReadinessState>('initializing');
  // Ref mirrors state so the polling closure always sees the latest value
  const readinessRef = useRef<ReadinessState>('initializing');

  const updateReadiness = useCallback((next: ReadinessState) => {
    if (readinessRef.current === next) return;
    readinessRef.current = next;
    setReadiness(next);
  }, []);

  const resetReadiness = useCallback(() => {
    updateReadiness('initializing');
  }, [updateReadiness]);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);
  const onBecameReadyRef = useRef(onBecameReady);
  onBecameReadyRef.current = onBecameReady;

  // ── Interval cleanup ─────────────────────────────────────────────────────
  const stopInterval = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // ── Per-frame detection ──────────────────────────────────────────────────
  const runFrame = useCallback(async () => {
    const video = videoRef.current;
    if (!mountedRef.current || !video || !_cachedDetector) return;
    // Wait until the video element has real pixel data
    if (video.readyState < 2 || video.videoWidth === 0) return;

    try {
      const poses = await _cachedDetector.estimatePoses(video);
      if (!mountedRef.current) return;

      const prevReady = readinessRef.current === 'ready';

      if (!poses || poses.length === 0) {
        if (readinessRef.current !== 'positioning') updateReadiness('positioning');
        return;
      }

      const isReady = evaluateFramingReadiness(
        poses[0].keypoints,
        video.videoHeight || video.clientHeight,
      );

      if (isReady && !prevReady) {
        updateReadiness('ready');
        onBecameReadyRef.current();
      } else if (!isReady && prevReady) {
        updateReadiness('positioning');
      } else if (!isReady && readinessRef.current === 'initializing') {
        updateReadiness('positioning');
      }
    } catch {
      // Non-fatal — skip this frame silently
    }
  }, [videoRef, updateReadiness]);

  // ── Main effect: start / stop detection based on `active` ───────────────
  useEffect(() => {
    if (!active) {
      stopInterval();
      return;
    }

    updateReadiness('initializing');

    const start = async () => {
      try {
        await ensureDetector();
        if (!mountedRef.current) return;

        // Got the detector — transition to "positioning" immediately so the
        // UI shows the amber banner while we wait for a good frame.
        if (readinessRef.current === 'initializing') {
          updateReadiness('positioning');
        }

        stopInterval();
        intervalRef.current = setInterval(runFrame, INTERVAL_MS);
      } catch (err) {
        // If TFJS / model fails to load (e.g. first visit with no network)
        // fall back gracefully: stay in "positioning" — never blocks the user.
        if (mountedRef.current) {
          console.warn('[usePoseReadiness] Detector load failed:', err);
          updateReadiness('positioning');
        }
      }
    };

    start();

    return () => {
      stopInterval();
    };
    // active changes trigger a fresh start/stop cycle
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  // ── Unmount cleanup ──────────────────────────────────────────────────────
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      stopInterval();
      // We intentionally do NOT dispose the detector here — it's cached at
      // module scope for reuse. It will be GC'd when the page is unloaded.
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { readiness, resetReadiness };
}
