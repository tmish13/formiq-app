import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import {
  Calendar,
  Eye,
  Plus,
  Filter,
  Search,
  Target,
  Dumbbell,
} from 'lucide-react';
import { Input } from '../components/ui/input';
import { useToast } from '../hooks/use-toast';
import AppLayout from '../components/layout/AppLayout';

// Import our backend services
import { formCheckService } from '../services/formCheckService';
import { FormCheck, ExerciseType, isMeaningfulScore } from '../types/formCheck';
import { logEvent } from '../utils/logEvent';

export default function AnalysisListPage() {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [formChecks, setFormChecks] = useState<FormCheck[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedExercise, setSelectedExercise] = useState<ExerciseType | 'all'>('all');


  useEffect(() => {
    loadFormChecks();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadFormChecks = async () => {
    try {
      setLoading(true);
      const formCheckData = await formCheckService.getHistory();
      setFormChecks(formCheckData);
    } catch (error) {
      console.error('Failed to load form checks:', error);
      logEvent('history_load_failed', { error: String(error) });
      toast({
        title: "Couldn't load your history",
        description: 'Pull down to refresh or try again.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  /**
   * Maps a posture score to a color class for the score percentage badge.
   * Thresholds: 75+ Strong (green), 60+ Solid (blue), 30+ Room to Improve (amber), else Needs Attention (red).
   */
  const getScoreColor = (score: number) => {
    if (score >= 75) return 'text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400';
    if (score >= 60) return 'text-blue-600 bg-blue-50 dark:bg-blue-900/20 dark:text-blue-400';
    if (score >= 30) return 'text-amber-600 bg-amber-50 dark:bg-amber-900/20 dark:text-amber-400';
    return 'text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400';
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-500 text-white">Completed</Badge>;
      case 'analyzing':
        return <Badge className="bg-blue-500 text-white animate-pulse">Analyzing…</Badge>;
      case 'pending':
        return <Badge className="bg-yellow-500 text-white">Pending</Badge>;
      case 'processing':
        return <Badge className="bg-blue-500 text-white">Processing</Badge>;
      case 'failed':
        return <Badge className="bg-red-500 text-white">Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  /**
   * A "valid" session is one that completed analysis and has a real score.
   * PostureV1 writes posture_score; the generic `score` field is a fallback.
   * Completed sessions with neither set were marked uncertain by the pipeline.
   */
  const isValidSession = (formCheck: FormCheck): boolean => {
    const effective = formCheck.posture_score ?? formCheck.score;
    return formCheck.status === 'completed' && effective != null;
  };

  /** Human-readable card title: "Squat · 185 lb", "Squat · 3 Reps", or "Squat · Single Rep". */
  const getCardTitle = (formCheck: FormCheck): string => {
    const slug = formCheck.exercise_type || formCheck.classified_exercise_slug || '';
    const exerciseName = slug === 'squat'
      ? 'Squat'
      : (formCheck.exercise_name ||
          (slug.replace(/_/g, ' ').charAt(0).toUpperCase() + slug.slice(1).replace(/_/g, ' '))) ||
        'Session';
    const weightLb = formCheck.weight_kg != null ? toLb(formCheck.weight_kg) : null;
    if (weightLb != null) return `${exerciseName} · ${weightLb} lb`;
    if (formCheck.reps != null && formCheck.reps > 1) return `${exerciseName} · ${formCheck.reps} Reps`;
    return `${exerciseName} · Single Rep`;
  };

  /**
   * Maps posture_score → short label + badge classes.
   * Tiers: 75%+ Strong (green), 60–75% Solid (blue), 30–60% Room to Improve (amber), <30% Needs Attention (red).
   */
  const getScoreBandLabel = (score: number): { label: string; className: string; dot: string } => {
    if (score >= 75) return {
      label: 'Strong',
      className: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 border border-green-200 dark:border-green-700',
      dot: 'bg-green-500',
    };
    if (score >= 60) return {
      label: 'Solid',
      className: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 border border-blue-200 dark:border-blue-700',
      dot: 'bg-blue-500',
    };
    if (score >= 30) return {
      label: 'Room to Improve',
      className: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border border-amber-200 dark:border-amber-700',
      dot: 'bg-amber-500',
    };
    return {
      label: 'Needs Attention',
      className: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 border border-red-200 dark:border-red-700',
      dot: 'bg-red-500',
    };
  };

  const filteredFormChecks = formChecks.filter((formCheck) => {
    const exerciseSlug = formCheck.exercise_type || formCheck.classified_exercise_slug || '';
    const matchesSearch =
      exerciseSlug.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (formCheck.created_at && new Date(formCheck.created_at).toLocaleDateString().includes(searchTerm));

    const matchesExercise = selectedExercise === 'all' || exerciseSlug.toLowerCase() === selectedExercise.toLowerCase();

    return matchesSearch && matchesExercise;
  });

  const exerciseTypes: (ExerciseType | 'all')[] = ['all', 'squat'];

  /** Count for each exercise type filter (for badge display). */
  const exerciseFilterCount = (type: ExerciseType | 'all'): number => {
    if (type === 'all') return formChecks.length;
    return formChecks.filter(fc =>
      (fc.exercise_type || fc.classified_exercise_slug || '') === type
    ).length;
  };

  const toLb = (kg: number | null | undefined): number | null =>
    kg == null ? null : Math.round(kg * 2.20462);

  const getDateLabel = (dateStr: string): string => {
    const date = new Date(dateStr);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    if (date.toDateString() === today.toDateString()) return 'Today';
    if (date.toDateString() === yesterday.toDateString()) return 'Yesterday';
    return date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  };

  // Session-to-session posture_score deltas (chronological order, valid sessions only)
  const sessionDeltaMap = useMemo(() => {
    const sorted = [...formChecks]
      .filter(fc => isMeaningfulScore(fc.posture_score))
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
    const map = new Map<string, number>();
    for (let i = 1; i < sorted.length; i++) {
      map.set(sorted[i].id, sorted[i].posture_score! - sorted[i - 1].posture_score!);
    }
    return map;
  }, [formChecks]);

  const groupedSessions = useMemo(() => {
    const sorted = [...filteredFormChecks]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    const groups: Array<{ label: string; items: FormCheck[] }> = [];
    for (const fc of sorted) {
      const label = getDateLabel(fc.created_at);
      const existing = groups.find(g => g.label === label);
      if (existing) existing.items.push(fc);
      else groups.push({ label, items: [fc] });
    }
    return groups;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filteredFormChecks]);

  return (
    <AppLayout>
      <div className="pb-24" style={{ paddingBottom: "max(env(safe-area-inset-bottom), 24px)" }}>
      <div className="px-4 py-6 space-y-6">
        {/* Page header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">History</h1>
            <p className="text-sm text-muted-foreground mt-0.5">Your past form checks</p>
          </div>
          <Button
            size="sm"
            className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700 rounded-xl"
            onClick={() => navigate('/record')}
          >
            <Plus className="w-4 h-4 mr-1.5" />
            New
          </Button>
        </div>

        {/* Search and Filter */}
        <div className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <Input
              type="text"
              placeholder="Search analyses..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 overflow-x-auto pb-2">
              <Filter className="w-4 h-4 text-gray-500 flex-shrink-0" />
              {exerciseTypes.map((type) => {
                const count = exerciseFilterCount(type);
                const label = type === 'all'
                  ? 'All'
                  : type.replace('_', ' ').charAt(0).toUpperCase() + type.slice(1).replace('_', ' ');
                return (
                  <Button
                    key={type}
                    variant={selectedExercise === type ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectedExercise(type)}
                    className="flex-shrink-0"
                  >
                    {label}
                    {count > 0 && (
                      <span className={`ml-1.5 text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                        selectedExercise === type
                          ? 'bg-white/20 text-white'
                          : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
                      }`}>
                        {count}
                      </span>
                    )}
                  </Button>
                );
              })}
            </div>
            <button
              className="ml-2 flex-shrink-0 text-xs text-muted-foreground border border-dashed border-gray-300 dark:border-gray-600 rounded-lg px-2.5 py-1.5 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              onClick={() => toast({ title: 'More filters coming soon!', description: 'Multi-exercise support is on the roadmap.', duration: 2500 })}
            >
              + Filters
            </button>
          </div>
        </div>

        {/* Analysis Stats */}
        {formChecks.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-blue-600">{formChecks.length}</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Total Analyses</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-green-600">
                  {formChecks.filter(fc => isValidSession(fc)).length}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Scored</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                {(() => {
                  const valid = formChecks.filter(fc => isMeaningfulScore(fc.posture_score ?? fc.score) && fc.status === 'completed');
                  const avg = valid.length > 0
                    ? Math.round(valid.reduce((sum, fc) => sum + ((fc.posture_score ?? fc.score) || 0), 0) / valid.length)
                    : null;
                  return (
                    <>
                      <div className="text-2xl font-bold text-purple-600">{avg != null ? `${avg}%` : '—'}</div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">Avg Score</div>
                    </>
                  );
                })()}
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-amber-600">
                  {formChecks.filter(fc => fc.status === 'completed' && !isValidSession(fc)).length}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Needs Retry</div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Analysis List */}
        <div className="space-y-3">
          {loading ? (
            <div className="space-y-3">
              {[0, 1, 2].map(i => (
                <div key={i} className="rounded-xl border border-border bg-card p-4 animate-pulse">
                  <div className="flex items-center gap-3">
                    <div className="w-11 h-11 rounded-lg bg-muted" />
                    <div className="flex-1 space-y-2">
                      <div className="h-3.5 bg-muted rounded w-2/5" />
                      <div className="h-3 bg-muted rounded w-1/3" />
                    </div>
                    <div className="w-12 h-8 bg-muted rounded" />
                  </div>
                </div>
              ))}
            </div>
          ) : filteredFormChecks.length === 0 ? (
            <Card>
              <CardContent className="p-8 text-center">
                <Target className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  {formChecks.length === 0 ? 'No Analyses Yet' : 'No Sessions Found'}
                </h3>
                <p className="text-gray-500 dark:text-gray-400 mb-5 text-sm leading-relaxed">
                  {formChecks.length === 0
                    ? 'Record your first squat to start building your training log.'
                    : selectedExercise !== 'all'
                    ? `No ${selectedExercise} sessions yet. Record your first one to start tracking your form.`
                    : 'Try adjusting your search or filter criteria.'}
                </p>
                <Button
                  onClick={() => navigate('/record')}
                  className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Go to Record
                </Button>
              </CardContent>
            </Card>
          ) : (
            groupedSessions.map((group, groupIdx) => {
              // Sort within each date group: valid sessions first, invalid/uncertain after
              const validItems   = group.items.filter(fc => isValidSession(fc));
              const invalidItems = group.items.filter(fc => !isValidSession(fc));
              const hasInvalid   = invalidItems.length > 0;

              const renderCard = (formCheck: FormCheck) => {
                const isValid     = isValidSession(formCheck);
                const isUncertain = formCheck.status === 'completed' && !isValid;

                return (
                  <Card
                    key={formCheck.id}
                    className={`cursor-pointer hover:shadow-md transition-shadow ${isUncertain ? 'opacity-60' : ''}`}
                    onClick={() => navigate(`/analysis/${formCheck.id}`)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-3">
                          {/* Exercise icon — consistent Dumbbell vector icon */}
                          <div className={`w-11 h-11 rounded-lg flex items-center justify-center ${
                            isUncertain
                              ? 'bg-amber-50 dark:bg-amber-900/20'
                              : 'bg-blue-100 dark:bg-blue-900/30'
                          }`}>
                            <Dumbbell className={`w-5 h-5 ${
                              isUncertain
                                ? 'text-amber-500 dark:text-amber-400'
                                : 'text-blue-600 dark:text-blue-400'
                            }`} />
                          </div>
                          <div>
                            <h3 className="font-semibold text-sm text-gray-900 dark:text-white leading-tight">
                              {getCardTitle(formCheck)}
                            </h3>
                            {/* Subtitle */}
                            {isUncertain ? (
                              <p className="text-xs text-amber-600 dark:text-amber-400 mt-0.5">
                                Recording angle unclear — try capturing from the side.
                              </p>
                            ) : (
                              <div className="flex items-center space-x-1.5 text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                                <Calendar className="w-3 h-3 flex-shrink-0" />
                                <span>
                                  {new Date(formCheck.created_at).toLocaleDateString('en-US', {
                                    month: 'short', day: 'numeric',
                                    hour: 'numeric', minute: '2-digit',
                                  })}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Right-hand badge area */}
                        <div className="text-right space-y-1 flex-shrink-0 ml-2">
                          {formCheck.status !== 'completed'
                            ? getStatusBadge(formCheck.status)
                            : isValid
                            ? (() => {
                              const effectiveScore = formCheck.posture_score ?? formCheck.score!;
                              const band  = getScoreBandLabel(effectiveScore);
                              const delta = sessionDeltaMap.get(formCheck.id);
                              return (
                                <>
                                  <div className={`text-sm font-bold px-2 py-1 rounded ${getScoreColor(effectiveScore)}`}>
                                    {Math.round(effectiveScore)}%
                                  </div>
                                  <span className={`text-xs px-1.5 py-0.5 rounded flex items-center gap-1 ${band.className}`}>
                                    <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${band.dot}`} />
                                    {band.label}
                                  </span>
                                  {delta != null && (
                                    <div className={`text-xs font-medium mt-0.5 ${delta >= 0 ? 'text-green-600' : 'text-amber-500'}`}>
                                      {delta >= 0 ? '+' : ''}{Math.round(delta)} vs prev
                                    </div>
                                  )}
                                </>
                              );
                            })()
                            : (
                              <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border border-amber-200 dark:border-amber-700">
                                Uncertain
                              </Badge>
                            )
                          }
                        </div>
                      </div>

                      {/* Bottom row */}
                      <div className="flex items-center justify-between pt-2.5 border-t border-gray-100 dark:border-gray-700/60">
                        <div className="flex items-center space-x-1.5 text-xs text-gray-500 dark:text-gray-400">
                          <Eye className="w-3 h-3" />
                          <span>View Details</span>
                        </div>
                        {isValid ? (
                          <span className="text-xs font-medium text-green-600 dark:text-green-400">
                            Analyzed
                          </span>
                        ) : isUncertain ? (
                          <span className="text-xs text-amber-500 dark:text-amber-400">
                            Try again
                          </span>
                        ) : null}
                      </div>
                    </CardContent>
                  </Card>
                );
              };

              return (
                <div key={group.label} className={`space-y-2 ${groupIdx > 0 ? 'mt-6' : ''}`}>
                  {/* Date section header — clear visual separation between days */}
                  <div className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-widest px-1 pt-1 pb-0.5 border-b border-gray-100 dark:border-gray-800/60">
                    {group.label}
                  </div>

                  {/* Valid sessions */}
                  {validItems.map(renderCard)}

                  {/* Uncertain/invalid sessions — separated with a dim divider */}
                  {hasInvalid && (
                    <>
                      {validItems.length > 0 && (
                        <div className="flex items-center gap-2 px-1 py-0.5">
                          <div className="flex-1 h-px bg-amber-200 dark:bg-amber-800/40" />
                          <span className="text-[10px] font-medium text-amber-500 dark:text-amber-500 uppercase tracking-wide">
                            Review needed
                          </span>
                          <div className="flex-1 h-px bg-amber-200 dark:bg-amber-800/40" />
                        </div>
                      )}
                      {invalidItems.map(renderCard)}
                    </>
                  )}
                </div>
              );
            })
          )}
        </div>


      </div>
      </div>
    </AppLayout>
  );
}
