import React, { useState } from 'react';
import { ArrowLeft, CheckSquare, Square } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';

const SECTIONS = [
  {
    title: 'Recording Test',
    color: 'border-blue-400',
    headerColor: 'text-blue-600 dark:text-blue-400',
    steps: [
      'Tap the record tab and select "Squat".',
      'Position your phone on the floor or a low surface — full body must be visible.',
      'Tap Record and perform one clean squat rep (3–6 seconds).',
      'Review the preview, then tap "Use This Rep".',
      'Verify you reach the /processing page and it shows the progress stages.',
    ],
    expected: 'You are redirected to the analysis results within 60 seconds.',
  },
  {
    title: 'Snapshot Test',
    color: 'border-purple-400',
    headerColor: 'text-purple-600 dark:text-purple-400',
    steps: [
      'Open any completed analysis.',
      'Look at the "Critical Moment" card — it should show a freeze-frame of your deepest squat position.',
      'Check the joint angle readout below the snapshot (Knee L/R and Hip).',
    ],
    expected: 'Snapshot shows a frame, not a spinner or "No snapshot" message.',
  },
  {
    title: 'Invalid Clip Test',
    color: 'border-amber-400',
    headerColor: 'text-amber-600 dark:text-amber-400',
    steps: [
      'Record a clip where most of your body is NOT in frame (e.g., only torso visible).',
      'Submit for analysis.',
      'Observe the result — the score should show "—" (dash) not a number.',
      'An amber "Why is analysis unavailable?" card should appear.',
    ],
    expected: 'App shows a clear reason (not a red error screen) and a "Re-record Video" button.',
  },
  {
    title: 'Tips Tab Test',
    color: 'border-green-400',
    headerColor: 'text-green-600 dark:text-green-400',
    steps: [
      'Open a completed analysis with a valid score.',
      'Tap the "Tips" tab.',
      'Review the "Primary Limiter" card — does it reflect the correct component?',
      'Review the "Personalized Recommendations" — do the drill suggestions make sense?',
    ],
    expected: 'No empty cards; each recommendation has a title, description, and "Practice drills" section.',
  },
  {
    title: 'Progress Test',
    color: 'border-orange-400',
    headerColor: 'text-orange-600 dark:text-orange-400',
    steps: [
      'Complete at least 2 analyses.',
      'Navigate to the Progress tab.',
      'Verify "Form Performance" section shows your average score and trend.',
      'Verify "Weight Performance" shows the chart (if you entered a weight).',
      'Check the "Session History" list — all sessions should be listed with a score badge.',
    ],
    expected: 'All stat cards populated; chart renders without error; session history matches your analyses.',
  },
] as const;

export default function BetaChecklistPage() {
  const navigate = useNavigate();
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const toggle = (key: string) =>
    setChecked(prev => ({ ...prev, [key]: !prev[key] }));

  const totalSteps = SECTIONS.reduce((sum, s) => sum + s.steps.length, 0);
  const doneSteps = Object.values(checked).filter(Boolean).length;
  const pct = Math.round((doneSteps / totalSteps) * 100);

  const handleFeedbackSubmit = () => {
    const payload = {
      category: 'Beta checklist',
      message: feedbackMsg,
      timestamp: new Date().toISOString(),
    };
    // TODO: wire /beta-feedback backend route
    console.log('BETA_FEEDBACK', payload);
    setSubmitted(true);
  };

  return (
    <AppLayout>
      <div
        className="px-4 py-5 max-w-2xl mx-auto space-y-6"
        style={{ paddingBottom: 'max(env(safe-area-inset-bottom), 96px)' }}
      >
        {/* Header */}
        <div>
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            FormIQ Beta Test Guide
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Follow each section to validate the core flows. Tap each step to mark it done.
          </p>
        </div>

        {/* Progress bar */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs text-gray-500">
            <span>{doneSteps} / {totalSteps} steps completed</span>
            <span>{pct}%</span>
          </div>
          <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all duration-300"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* Sections */}
        {SECTIONS.map((section, si) => (
          <div key={section.title} className={`border-l-4 ${section.color} pl-4 space-y-3`}>
            <h2 className={`text-base font-semibold ${section.headerColor}`}>
              {si + 1}. {section.title}
            </h2>
            <ul className="space-y-2">
              {section.steps.map((step, i) => {
                const key = `${si}-${i}`;
                const done = !!checked[key];
                return (
                  <li
                    key={key}
                    onClick={() => toggle(key)}
                    className="flex items-start gap-2.5 cursor-pointer group"
                  >
                    {done ? (
                      <CheckSquare className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                    ) : (
                      <Square className="w-4 h-4 text-gray-400 dark:text-gray-500 flex-shrink-0 mt-0.5 group-hover:text-gray-600 dark:group-hover:text-gray-300" />
                    )}
                    <span className={`text-sm leading-snug ${done ? 'line-through text-gray-400 dark:text-gray-500' : 'text-gray-700 dark:text-gray-300'}`}>
                      {step}
                    </span>
                  </li>
                );
              })}
            </ul>
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg px-3 py-2">
              <p className="text-xs text-gray-500 dark:text-gray-400">
                <span className="font-semibold text-gray-600 dark:text-gray-300">Expected: </span>
                {section.expected}
              </p>
            </div>
          </div>
        ))}

        {/* Feedback section */}
        <div className="border-t border-gray-200 dark:border-gray-700 pt-5 space-y-3">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">Overall Feedback</h2>

          {submitted ? (
            <div className="rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 px-4 py-3">
              <p className="text-sm text-green-700 dark:text-green-300 font-medium">
                Thank you — feedback submitted.
              </p>
            </div>
          ) : showFeedback ? (
            <div className="space-y-3">
              <textarea
                value={feedbackMsg}
                onChange={e => setFeedbackMsg(e.target.value)}
                placeholder="What worked well? What felt broken or confusing?"
                rows={5}
                className="w-full px-3 py-2.5 border border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder:text-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30 resize-none"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => setShowFeedback(false)}
                  className="flex-1 py-2.5 border border-gray-300 dark:border-gray-600 rounded-xl text-sm text-gray-600 dark:text-gray-300"
                >
                  Cancel
                </button>
                <button
                  onClick={handleFeedbackSubmit}
                  disabled={!feedbackMsg.trim()}
                  className="flex-1 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-semibold disabled:opacity-40 transition-colors"
                >
                  Submit Feedback
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowFeedback(true)}
              className="w-full py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-xl text-sm font-semibold transition-all"
            >
              Submit Overall Feedback
            </button>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
