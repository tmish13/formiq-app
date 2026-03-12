import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle } from 'lucide-react';
import apiService from '../services/apiService';
import { formCheckService } from '../services/formCheckService';
import { progressService } from '../services/progressService';

const POLL_INTERVAL_MS = 2000;

// Synthetic progress: ~0.4% per 200 ms → reaches 96% in ~48 s naturally.
// Backend navigation unmounts the component, clearing the interval automatically.
const TICK_MS = 200;
const TICK_STEP = 0.4;
const MAX_SYNTH = 96; // never reach 100 synthetically — backend navigation triggers that

const STAGES = [
  'Reading your movement',
  'Identifying your mechanics',
  'Scoring your form',
  'Building your feedback',
] as const;

/** Map known backend error strings to friendly copy. */
function friendlyError(err: string | null | undefined): string {
  if (!err) return 'Something went wrong. Try recording a new clip.';
  const e = err.toLowerCase();
  if (e.includes('duration') || e.includes('too_long') || e.includes('too long'))
    return 'Clip too long for single-rep analysis. Record one rep (3–6 seconds) and try again.';
  if (e.includes('visibility') || e.includes('body') || e.includes('landmark'))
    return 'We couldn\'t read your body position clearly. Try better lighting with your full body in frame.';
  if (e.includes('motion') || e.includes('frame'))
    return 'Not enough clear motion was detected. Make sure you complete a full rep and keep the camera steady.';
  return 'Something went wrong during analysis. Check your video and try again.';
}

// Stage i becomes "active" when synthProgress >= STAGE_THRESHOLDS[i]
const STAGE_THRESHOLDS = [0, 25, 50, 75];

const ModernProcessingPage: React.FC = () => {
  const { videoId } = useParams<{ videoId: string }>();
  const navigate = useNavigate();
  const [synthProgress, setSynthProgress] = React.useState(0);
  const [error, setError] = React.useState<string | null>(null);

  // ── Synthetic progress ticker ──────────────────────────────────────────────
  React.useEffect(() => {
    const id = setInterval(() => {
      setSynthProgress(p => {
        const next = p + TICK_STEP;
        if (next >= MAX_SYNTH) {
          clearInterval(id);
          return MAX_SYNTH;
        }
        return next;
      });
    }, TICK_MS);
    return () => clearInterval(id);
  }, []);

  // ── Backend polling (logic unchanged) ────────────────────────────────────
  React.useEffect(() => {
    if (!videoId) return;

    let cancelled = false;

    const poll = async () => {
      try {
        const data = await apiService.getVideoStatus(videoId);

        if (cancelled) return;

        if (data.status === 'ready' || data.status === 'completed') {
          setSynthProgress(100);
          // Invalidate progress cache so ProgressPage reflects this new analysis immediately.
          progressService.clearCache();
          try {
            const formCheck = await formCheckService.getFormCheck(videoId);
            if (!cancelled) {
              navigate(`/analysis/${formCheck.id}`, { replace: true });
            }
          } catch {
            if (!cancelled) {
              navigate(`/analysis/${videoId}`, { replace: true });
            }
          }
          return;
        }

        if (data.status === 'failed' || data.error) {
          setError(friendlyError(data.error));
          return;
        }

        setTimeout(poll, POLL_INTERVAL_MS);
      } catch (err) {
        if (cancelled) return;
        console.error('Status poll error:', err);
        setTimeout(poll, POLL_INTERVAL_MS * 2);
      }
    };

    poll();

    return () => {
      cancelled = true;
    };
  }, [videoId, navigate]);

  // ── Derived display values ────────────────────────────────────────────────
  const progress = Math.min(Math.round(synthProgress), 100);

  // currentStageIdx: highest stage whose threshold has been crossed
  const currentStageIdx = STAGE_THRESHOLDS.reduce<number>(
    (cur, threshold, i) => (progress >= threshold ? i : cur),
    0,
  );

  const isAllDone = progress >= 100;

  return (
    <div
      className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col"
      style={{ opacity: 1, transition: 'opacity 0.3s ease' }}
    >
      {/* ── Minimal header ─────────────────────────────────────────────────── */}
      <div className="flex items-center px-4 pt-12 pb-3">
        <button
          aria-label="Go back"
          onClick={() => navigate(-1)}
          className="p-2 -ml-2 rounded-full text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <span className="ml-2 text-sm font-semibold text-gray-700 dark:text-gray-300">FormIQ</span>
        <span className="ml-1.5 text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400">
          Beta
        </span>
      </div>

      {/* ── Main content ────────────────────────────────────────────────────── */}
      {error ? (
        <div className="flex-1 flex items-center justify-center px-6">
          <div className="text-center space-y-5 max-w-xs">
            <p className="text-base font-semibold text-red-600 dark:text-red-400">Analysis didn't complete</p>
            <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{error}</p>
            <p className="text-xs text-gray-400 dark:text-gray-500">
              Tip: one squat rep · 3–6 sec · side or back angle · full body visible
            </p>
            <button
              onClick={() => navigate('/record')}
              className="px-5 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 transition-colors"
            >
              Record New Clip
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center px-6 gap-8 pb-12">

          {/* Title */}
          <div className="text-center space-y-2 max-w-xs">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
              Analyzing your rep
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
              This usually takes 30–60 seconds.
            </p>
          </div>

          {/* Spinner */}
          <div
            className="w-9 h-9 rounded-full border-4 border-blue-200 dark:border-blue-900 border-t-blue-500 dark:border-t-blue-400 animate-spin"
            role="status"
            aria-label="Analyzing"
          />

          {/* Progress bar */}
          <div className="w-full max-w-sm space-y-1.5">
            <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 transition-all duration-300 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex justify-end">
              <span className="text-xs font-mono text-gray-400 dark:text-gray-500">{progress}%</span>
            </div>
          </div>

          {/* Stage list */}
          <div className="w-full max-w-sm space-y-3">
            {STAGES.map((label, i) => {
              const isComplete = isAllDone || i < currentStageIdx;
              const isActive   = !isAllDone && i === currentStageIdx;
              // isPending: neither complete nor active
              return (
                <div key={i} className="flex items-center gap-3">
                  {isComplete ? (
                    <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
                  ) : isActive ? (
                    <span className="w-5 h-5 flex-shrink-0 rounded-full bg-blue-500 animate-pulse" />
                  ) : (
                    <span className="w-5 h-5 flex-shrink-0 rounded-full border-2 border-gray-300 dark:border-gray-600" />
                  )}
                  <span
                    className={`text-sm leading-snug transition-colors duration-200 ${
                      isComplete
                        ? 'text-gray-400 dark:text-gray-500'
                        : isActive
                        ? 'text-blue-600 dark:text-blue-400 font-medium'
                        : 'text-gray-400 dark:text-gray-500'
                    }`}
                  >
                    {label}
                  </span>
                </div>
              );
            })}
          </div>

        </div>
      )}
    </div>
  );
};

export default ModernProcessingPage;
