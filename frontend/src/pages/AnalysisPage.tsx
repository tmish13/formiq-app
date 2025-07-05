import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  Target,
  TrendingUp,
  RotateCcw,
  Share,
  BookOpen,
  Play,
  Sparkles,
  Brain,
  ArrowLeft,
  LoaderIcon,
} from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import AppLayout from '../components/layout/AppLayout';

// Import our backend services
import { formCheckService } from '../services/formCheckService';
import { FormCheck } from '../types/formCheck';

interface AnalysisBreakdown {
  category: string;
  score: number;
  status: 'excellent' | 'good' | 'warning' | 'poor';
  feedback: string;
  icon: string;
  improvement: string;
  keyFrames?: number[];
}

interface AIRecommendation {
  icon: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  exercise: string;
  duration: string;
}

export default function AnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [formCheck, setFormCheck] = useState<FormCheck | null>(null);
  const [mlAnalysis, setMlAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showDetails, setShowDetails] = useState<number | null>(null);
  const [breakdown, setBreakdown] = useState<AnalysisBreakdown[]>([]);
  const [recommendations, setRecommendations] = useState<AIRecommendation[]>([]);

  useEffect(() => {
    if (id) {
      loadAnalysisData(id);
    } else {
      // Load latest analysis if no ID provided
      loadLatestAnalysis();
    }
  }, [id]);

  const loadAnalysisData = async (formCheckId: string) => {
    try {
      setLoading(true);
      
      // Load form check data
      const formCheckData = await formCheckService.getFormCheck(formCheckId);
      setFormCheck(formCheckData);
      
      // Load ML analysis if available
      try {
        const mlData = await formCheckService.getMLAnalysis(formCheckId);
        setMlAnalysis(mlData);
        
        // Generate breakdown from ML data
        if (mlData.ml_scores) {
          const generatedBreakdown = generateBreakdownFromML(mlData.ml_scores);
          setBreakdown(generatedBreakdown);
          
          // Generate recommendations
          const generatedRecommendations = generateRecommendations(generatedBreakdown, formCheckData.exercise_type);
          setRecommendations(generatedRecommendations);
        }
      } catch (mlError) {
        console.warn('ML analysis not available, using fallback data');
        setBreakdown(getFallbackBreakdown(formCheckData));
        setRecommendations(getFallbackRecommendations(formCheckData.exercise_type));
      }
    } catch (error) {
      console.error('Failed to load analysis:', error);
      toast({
        title: 'Analysis Error',
        description: 'Failed to load analysis data.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const loadLatestAnalysis = async () => {
    try {
      setLoading(true);
      const latestFormChecks = await formCheckService.getLatestFormChecks(1);
      
      if (latestFormChecks.length > 0) {
        await loadAnalysisData(latestFormChecks[0].id);
      } else {
        toast({
          title: 'No Analysis Found',
          description: 'No recent analysis available. Record a video first.',
          variant: 'destructive',
        });
        navigate('/record');
      }
    } catch (error) {
      console.error('Failed to load latest analysis:', error);
      navigate('/record');
    }
  };

  const generateBreakdownFromML = (mlScores: any): AnalysisBreakdown[] => {
    const breakdown: AnalysisBreakdown[] = [];
    
    if (mlScores.posture_score !== undefined) {
      breakdown.push({
        category: 'Posture',
        score: Math.round(mlScores.posture_score * 100),
        status: getScoreStatus(mlScores.posture_score * 100),
        feedback: getPostureFeedback(mlScores.posture_score * 100),
        icon: '🏋️',
        improvement: '+3%', // Would come from comparison with previous
      });
    }
    
    if (mlScores.stability_score !== undefined) {
      breakdown.push({
        category: 'Stability',
        score: Math.round(mlScores.stability_score * 100),
        status: getScoreStatus(mlScores.stability_score * 100),
        feedback: getStabilityFeedback(mlScores.stability_score * 100),
        icon: '⚖️',
        improvement: '+2%',
      });
    }
    
    if (mlScores.depth_score !== undefined) {
      breakdown.push({
        category: 'Depth',
        score: Math.round(mlScores.depth_score * 100),
        status: getScoreStatus(mlScores.depth_score * 100),
        feedback: getDepthFeedback(mlScores.depth_score * 100),
        icon: '📏',
        improvement: '+5%',
      });
    }

    return breakdown;
  };

  const getFallbackBreakdown = (formCheck: FormCheck): AnalysisBreakdown[] => {
    const overallScore = formCheck.score || 85;
    
    return [
      {
        category: 'Depth',
        score: Math.min(95, overallScore + 10),
        status: 'excellent',
        feedback: 'Excellent depth achieved - hitting parallel consistently',
        icon: '📏',
        improvement: '+6%',
        keyFrames: [2, 4, 6, 8, 10],
      },
      {
        category: 'Posture',
        score: Math.max(65, overallScore - 15),
        status: overallScore > 80 ? 'good' : 'warning',
        feedback: overallScore > 80 ? 'Good neutral spine maintained throughout movement' : 'Minor posture issues detected - focus on core engagement',
        icon: '🏋️',
        improvement: '+4%',
        keyFrames: [1, 3, 5, 7, 9],
      },
      {
        category: 'Stability',
        score: Math.max(70, overallScore - 5),
        status: overallScore > 85 ? 'excellent' : 'good',
        feedback: overallScore > 85 ? 'Perfect controlled movement throughout' : 'Minor balance shifts - consider wider stance',
        icon: '⚖️',
        improvement: '+5%',
        keyFrames: [2, 4, 6, 8],
      },
    ];
  };

  const generateRecommendations = (breakdown: AnalysisBreakdown[], exerciseType: string): AIRecommendation[] => {
    const recommendations: AIRecommendation[] = [];
    
    // Find areas for improvement
    const weakestAreas = breakdown
      .filter(item => item.score < 80)
      .sort((a, b) => a.score - b.score);
    
    if (weakestAreas.length > 0) {
      const weakest = weakestAreas[0];
      recommendations.push({
        icon: '🎯',
        title: `Improve ${weakest.category}`,
        description: getImprovementSuggestion(weakest.category, exerciseType),
        priority: 'high',
        exercise: getRecommendedExercise(weakest.category, exerciseType),
        duration: '3 sets of 8-12 reps',
      });
    }
    
    // Add general recommendations
    recommendations.push({
      icon: '💪',
      title: 'Strength Development',
      description: `Great ${exerciseType} form! Try adding progressive overload to build strength.`,
      priority: 'medium',
      exercise: `Weighted ${exerciseType}s or single-leg variations`,
      duration: '3 sets of 5-8 reps',
    });
    
    if (breakdown.some(item => item.score > 90)) {
      recommendations.push({
        icon: '🔄',
        title: 'Advanced Progressions',
        description: 'Your form is excellent! Ready for advanced variations.',
        priority: 'low',
        exercise: `Jump ${exerciseType}s or pause ${exerciseType}s`,
        duration: 'Progress gradually',
      });
    }
    
    return recommendations;
  };

  const getFallbackRecommendations = (exerciseType: string): AIRecommendation[] => [
    {
      icon: '🦵',
      title: 'Knee Tracking',
      description: 'Push knees out during descent. Try the "spread the floor" cue with your feet.',
      priority: 'high',
      exercise: 'Wall sits with external rotation focus',
      duration: '2-3 sets of 30 seconds',
    },
    {
      icon: '💪',
      title: 'Depth Control',
      description: 'Your depth is excellent! Try adding pause squats to build strength at the bottom.',
      priority: 'medium',
      exercise: 'Pause squats (2-second hold)',
      duration: '3 sets of 5 reps',
    },
    {
      icon: '🔄',
      title: 'Tempo Mastery',
      description: 'Perfect tempo control. Continue with 2-1-2 pattern for optimal muscle engagement.',
      priority: 'low',
      exercise: 'Continue current tempo work',
      duration: 'Maintain consistency',
    },
  ];

  const getScoreStatus = (score: number): 'excellent' | 'good' | 'warning' | 'poor' => {
    if (score >= 90) return 'excellent';
    if (score >= 80) return 'good';
    if (score >= 60) return 'warning';
    return 'poor';
  };

  const getPostureFeedback = (score: number): string => {
    if (score >= 90) return 'Excellent posture maintained throughout the movement';
    if (score >= 80) return 'Good posture with minor areas for improvement';
    if (score >= 60) return 'Moderate posture issues - focus on core stability';
    return 'Significant posture concerns - work on alignment';
  };

  const getStabilityFeedback = (score: number): string => {
    if (score >= 90) return 'Perfect stability and control throughout movement';
    if (score >= 80) return 'Good stability with occasional minor shifts';
    if (score >= 60) return 'Moderate stability issues - work on balance';
    return 'Significant stability concerns - focus on core strength';
  };

  const getDepthFeedback = (score: number): string => {
    if (score >= 90) return 'Excellent depth achieved consistently';
    if (score >= 80) return 'Good depth with room for minor improvement';
    if (score >= 60) return 'Moderate depth issues - work on flexibility';
    return 'Insufficient depth - focus on mobility work';
  };

  const getImprovementSuggestion = (category: string, exerciseType: string): string => {
    const suggestions = {
      'Posture': `Focus on maintaining neutral spine throughout the ${exerciseType}. Engage your core before starting the movement.`,
      'Stability': `Work on balance and core strength. Consider using a wider stance for better stability during ${exerciseType}s.`,
      'Depth': `Improve ankle and hip mobility to achieve better depth in your ${exerciseType}s. Practice bodyweight variations first.`,
    };
    return suggestions[category as keyof typeof suggestions] || `Continue working on your ${category.toLowerCase()} for better ${exerciseType} performance.`;
  };

  const getRecommendedExercise = (category: string, exerciseType: string): string => {
    const exercises = {
      'Posture': 'Dead bugs and bird dogs for core stability',
      'Stability': 'Single-leg stands and balance board work',
      'Depth': 'Deep goblet squats and ankle mobility stretches',
    };
    return exercises[category as keyof typeof exercises] || `Focused ${exerciseType} practice`;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'excellent':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'good':
        return <CheckCircle className="w-5 h-5 text-blue-500" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      case 'poor':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <CheckCircle className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'excellent':
        return 'text-green-600';
      case 'good':
        return 'text-blue-600';
      case 'warning':
        return 'text-yellow-600';
      case 'poor':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'border-l-red-500 bg-red-50 dark:bg-red-900/20';
      case 'medium':
        return 'border-l-yellow-500 bg-yellow-50 dark:bg-yellow-900/20';
      case 'low':
        return 'border-l-green-500 bg-green-50 dark:bg-green-900/20';
      default:
        return 'border-l-gray-500 bg-gray-50 dark:bg-gray-900/20';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <LoaderIcon className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-gray-600 dark:text-gray-400">Loading analysis...</p>
        </div>
      </div>
    );
  }

  if (!formCheck) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 dark:text-gray-400 mb-4">Analysis not found</p>
          <Button onClick={() => navigate('/record')}>
            <RotateCcw className="w-4 h-4 mr-2" />
            Record New Video
          </Button>
        </div>
      </div>
    );
  }

  const overallScore = formCheck.score || 85;
  const exerciseDisplayName = formCheck.exercise_type.charAt(0).toUpperCase() + formCheck.exercise_type.slice(1);

  return (
    <AppLayout>
      <div className="pb-24" style={{ paddingBottom: "max(env(safe-area-inset-bottom), 24px)" }}>
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-4">
        <div className="flex items-center justify-between">
          <Button 
            variant="ghost" 
            size="sm"
            onClick={() => navigate('/')}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Analysis Results</h1>
          <div className="w-16" />
        </div>
      </div>

      <div className="px-4 py-6 space-y-6">
        {/* Analysis Header */}
        <Card className="bg-gradient-to-r from-blue-500 to-purple-600 text-white border-0">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h1 className="text-2xl font-bold mb-1">Analysis Complete</h1>
                <p className="text-blue-100">
                  {new Date(formCheck.created_at).toLocaleDateString('en-US', {
                    weekday: 'short',
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                </p>
              </div>
              <div className="text-center">
                <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mb-2">
                  <span className="text-2xl font-bold">{overallScore}</span>
                </div>
                <p className="text-sm text-blue-100">Form Score</p>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="text-center">
                  <p className="text-lg font-bold">5</p>
                  <p className="text-xs text-blue-100">Reps</p>
                </div>
                <div className="text-center">
                  <p className="text-lg font-bold">🏋️</p>
                  <p className="text-xs text-blue-100">{exerciseDisplayName}</p>
                </div>
              </div>
              <div className="text-right">
                <Badge className="bg-green-500/20 text-green-100 border-green-400">
                  <TrendingUp className="w-3 h-3 mr-1" />
                  AI Analyzed
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Form Breakdown */}
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Form Breakdown</h2>
          <div className="space-y-3">
            {breakdown.map((item, index) => (
              <Card key={index} className="border-0 shadow-sm">
                <CardContent className="p-4">
                  <div
                    className="flex items-center justify-between cursor-pointer"
                    onClick={() => setShowDetails(showDetails === index ? null : index)}
                  >
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(item.status)}
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white">{item.category}</h4>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          {item.feedback.length > 40 && showDetails !== index
                            ? item.feedback.substring(0, 40) + '...'
                            : item.feedback}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="flex items-center space-x-2">
                        <span className={`text-lg font-bold ${getStatusColor(item.status)}`}>{item.score}%</span>
                        <span className="text-sm text-green-600 font-medium">{item.improvement}</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-3">
                    <Progress value={item.score} className="h-2" />
                  </div>

                  {showDetails === index && (
                    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                      <div className="space-y-3">
                        <div>
                          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Key Analysis Points:
                          </p>
                          <p className="text-sm text-gray-600 dark:text-gray-400">{item.feedback}</p>
                        </div>
                        {item.keyFrames && (
                          <div>
                            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Analyzed Frames:</p>
                            <div className="flex space-x-2">
                              {item.keyFrames.map((frame, idx) => (
                                <Badge key={idx} variant="outline" className="text-xs">
                                  Frame {frame}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* AI Recommendations */}
        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Brain className="w-5 h-5 text-purple-600" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">AI Recommendations</h2>
            <Badge variant="secondary" className="bg-purple-100 text-purple-800 text-xs">
              Personalized
            </Badge>
          </div>
          <div className="space-y-4">
            {recommendations.map((rec, index) => (
              <Card key={index} className={`border-l-4 ${getPriorityColor(rec.priority)} border-0 shadow-sm`}>
                <CardContent className="p-4">
                  <div className="flex items-start space-x-3">
                    <div className="text-2xl">{rec.icon}</div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-semibold text-gray-900 dark:text-white">{rec.title}</h4>
                        <Badge
                          variant="outline"
                          className={`text-xs ${
                            rec.priority === 'high'
                              ? 'border-red-200 text-red-700'
                              : rec.priority === 'medium'
                                ? 'border-yellow-200 text-yellow-700'
                                : 'border-green-200 text-green-700'
                          }`}
                        >
                          {rec.priority} priority
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 leading-relaxed">{rec.description}</p>
                      <div className="bg-white/50 dark:bg-gray-800/50 rounded-lg p-3">
                        <div className="flex items-center space-x-2 mb-2">
                          <Play className="w-4 h-4 text-blue-600" />
                          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Recommended Exercise:</p>
                        </div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">{rec.exercise}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">{rec.duration}</p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* ML Scores Display */}
        {mlAnalysis?.ml_scores && (
          <Card className="border-0 shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2 text-base">
                <Target className="w-5 h-5 text-blue-600" />
                <span>ML Analysis Scores</span>
              </CardTitle>
              <CardDescription>Detailed machine learning assessment</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {mlAnalysis.ml_scores.posture_score !== undefined && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Posture Score</span>
                    <span className="text-sm text-blue-600 font-bold">
                      {Math.round(mlAnalysis.ml_scores.posture_score * 100)}%
                    </span>
                  </div>
                )}
                {mlAnalysis.ml_scores.stability_score !== undefined && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Stability Score</span>
                    <span className="text-sm text-green-600 font-bold">
                      {Math.round(mlAnalysis.ml_scores.stability_score * 100)}%
                    </span>
                  </div>
                )}
                {mlAnalysis.ml_scores.depth_score !== undefined && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Depth Score</span>
                    <span className="text-sm text-purple-600 font-bold">
                      {Math.round(mlAnalysis.ml_scores.depth_score * 100)}%
                    </span>
                  </div>
                )}
                {mlAnalysis.ml_scores.confidence !== undefined && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">AI Confidence</span>
                    <span className="text-sm text-gray-600 font-bold">
                      {Math.round(mlAnalysis.ml_scores.confidence * 100)}%
                    </span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Action Buttons */}
        <div className="grid grid-cols-2 gap-3">
          <Button 
            className="h-12 bg-blue-600 hover:bg-blue-700"
            onClick={() => navigate('/progress')}
          >
            <Target className="w-4 h-4 mr-2" />
            View Progress
          </Button>
          <Button 
            variant="outline" 
            className="h-12 bg-transparent"
            onClick={() => {
              // Share functionality
              if (navigator.share && formCheck) {
                navigator.share({
                  title: 'FormIQ Analysis Results',
                  text: `I scored ${overallScore}% on my ${exerciseDisplayName} form analysis!`,
                  url: window.location.href,
                });
              }
            }}
          >
            <Share className="w-4 h-4 mr-2" />
            Share Results
          </Button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Button 
            variant="outline" 
            className="h-12 bg-transparent"
            onClick={() => navigate('/analysis')}
          >
            <BookOpen className="w-4 h-4 mr-2" />
            All Analyses
          </Button>
          <Button
            variant="outline"
            className="h-12 bg-transparent"
            onClick={() => navigate('/record')}
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            New Analysis
          </Button>
        </div>

        {/* Success Banner */}
        {overallScore >= 80 && (
          <Card className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border-green-200 dark:border-green-800">
            <CardContent className="p-4">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
                  <Sparkles className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <h4 className="font-semibold text-green-900 dark:text-green-100">Excellent Form!</h4>
                  <p className="text-sm text-green-700 dark:text-green-200">
                    Great technique on your {exerciseDisplayName}. Keep up the excellent work!
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
      </div>
    </AppLayout>
  );
}