/**
 * Lightweight client-side event logger.
 * Writes to console and attempts a fire-and-forget POST to /client-logs.
 */
export const logEvent = (name: string, payload?: Record<string, unknown>): void => {
  const entry = {
    event: name,
    timestamp: new Date().toISOString(),
    ...payload,
  };
  console.log('[FormIQ]', entry);
  // Best-effort POST — never blocks the UI
  try {
    const token = localStorage.getItem('formiq_auth_token');
    const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
    fetch(`${baseUrl}/client-logs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(entry),
      keepalive: true,
    }).catch(() => {}); // fire-and-forget, ignore all errors
  } catch {
    // never throw from logEvent
  }
};

// ---------------------------------------------------------------------------
// Beta event instrumentation
// ---------------------------------------------------------------------------

const BETA_STATS_KEY = 'formiq_beta_stats';

interface BetaStats {
  analysis_success: number;
  analysis_failed: number;
  snapshot_missing: number;
  invalid_clip_detected: number;
  last_analysis_at?: string;
}

function _updateBetaStats(eventName: string): void {
  try {
    const raw = localStorage.getItem(BETA_STATS_KEY);
    const stats: BetaStats = raw
      ? JSON.parse(raw)
      : { analysis_success: 0, analysis_failed: 0, snapshot_missing: 0, invalid_clip_detected: 0 };
    if (eventName === 'analysis_success') {
      stats.analysis_success = (stats.analysis_success ?? 0) + 1;
      stats.last_analysis_at = new Date().toISOString();
    } else if (eventName === 'analysis_failed') {
      stats.analysis_failed = (stats.analysis_failed ?? 0) + 1;
    } else if (eventName === 'snapshot_missing') {
      stats.snapshot_missing = (stats.snapshot_missing ?? 0) + 1;
    } else if (eventName === 'invalid_clip_detected') {
      stats.invalid_clip_detected = (stats.invalid_clip_detected ?? 0) + 1;
    }
    localStorage.setItem(BETA_STATS_KEY, JSON.stringify(stats));
  } catch {
    // never throw
  }
}

/**
 * Lightweight beta diagnostics event logger.
 * - Always console.logs (dev + prod)
 * - Attempts a non-blocking POST to /beta-events (silently ignores failures)
 * - Updates local aggregated stats in localStorage
 */
export const logBetaEvent = (
  eventName: string,
  metadata?: Record<string, unknown>,
): void => {
  const entry = {
    event: eventName,
    timestamp: new Date().toISOString(),
    ...metadata,
  };
  console.log('[BetaEvent]', entry);
  _updateBetaStats(eventName);
  // Note: backend /beta-events route is not yet implemented — HTTP POST removed
  // to eliminate 404 spam. Stats are persisted locally in localStorage.
};

/** Read aggregated beta stats from localStorage for diagnostics panel. */
export const getBetaStats = (): BetaStats => {
  try {
    const raw = localStorage.getItem(BETA_STATS_KEY);
    if (raw) return JSON.parse(raw) as BetaStats;
  } catch {
    // ignore
  }
  return { analysis_success: 0, analysis_failed: 0, snapshot_missing: 0, invalid_clip_detected: 0 };
};
