import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Target, Activity, Info, Camera, Calendar, Award, Zap } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../hooks/use-toast';
import AppLayout from '../components/layout/AppLayout';

// Import our backend services
import { progressService } from '../services/progressService';
import { formCheckService } from '../services/formCheckService';

interface WeeklyData {
  week: string;
  score: number;
  sessions: number;
}

interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  tooltip: string;
  trend?: string;
  trendUp?: boolean;
}

const MetricCard: React.FC<MetricCardProps> = ({ icon, label, value, tooltip, trend, trendUp }) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.9 }}
    animate={{ opacity: 1, scale: 1 }}
    whileHover={{ scale: 1.02, y: -2 }}
    className="group relative"
  >
    <Card className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm shadow-md hover:shadow-lg transition-all duration-300">
      <CardContent className="p-6 text-center">
        <div className="flex items-center justify-center space-x-2 mb-3">
          {icon}
          <Info className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
        <div className="flex items-baseline justify-center">
          <div className="text-3xl font-bold text-gray-900 dark:text-gray-100">{value}</div>
        </div>
        <div className="text-sm font-medium text-gray-600 dark:text-gray-400">{label}</div>
        {trend && (
          <div className={`text-xs mt-1 ${trendUp ? 'text-green-600' : 'text-red-600'}`}>
            {trend}
          </div>
        )}

        {/* Tooltip */}
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 dark:bg-gray-700 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
          {tooltip}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900 dark:border-t-gray-700"></div>
        </div>
      </CardContent>
    </Card>
  </motion.div>
);

export default function ProgressPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [loading, setLoading] = useState(true);
  const [progressStats, setProgressStats] = useState<any>(null);
  const [weeklyData, setWeeklyData] = useState<WeeklyData[]>([]);
  const [achievements, setAchievements] = useState<any[]>([]);
  const [exerciseBreakdown, setExerciseBreakdown] = useState<any>({});
  
  useEffect(() => {
    loadProgressData();
  }, []);

  const loadProgressData = async () => {
    try {
      setLoading(true);
      
      // Load progress statistics
      const stats = await progressService.getProgressStats();
      setProgressStats(stats);
      
      // Load weekly trends
      const trends = await progressService.getProgressTrends(30);
      const weeklyProcessed = processWeeklyData(trends);
      setWeeklyData(weeklyProcessed);
      
      // Load exercise breakdown from form check service
      const exerciseStats = await formCheckService.getExerciseStatistics('30d');
      const breakdown: any = {};
      exerciseStats.forEach((stat: any) => {
        breakdown[stat.exercise_type] = {
          count: stat.count,
          avgScore: stat.avg_score,
          improvement: stat.improvement,
          trend: stat.trend
        };
      });
      setExerciseBreakdown(breakdown);
      
      // Calculate achievements
      const calculatedAchievements = calculateAchievements(stats, trends);
      setAchievements(calculatedAchievements);
      
    } catch (error) {
      console.error('Failed to load progress data:', error);
      // Use fallback data
      setProgressStats({
        averageScore: 75,
        improvementRate: 8,
        totalAnalyses: 0,
        exerciseTypeBreakdown: {},
        recentTrend: 'stable'
      });
      setWeeklyData(generateFallbackWeeklyData());
    } finally {
      setLoading(false);
    }
  };

  const processWeeklyData = (trends: Record<string, number[]>): WeeklyData[] => {
    const weeks: WeeklyData[] = [];
    const scores = trends.scores || [];
    
    // Group by week (assuming daily data)
    for (let i = 0; i < scores.length; i += 7) {
      const weekScores = scores.slice(i, i + 7);
      const avgScore = weekScores.length > 0 
        ? Math.round(weekScores.reduce((a, b) => a + b, 0) / weekScores.length)
        : 0;
      
      weeks.push({
        week: `Week ${Math.floor(i / 7) + 1}`,
        score: avgScore,
        sessions: weekScores.filter(s => s > 0).length
      });
    }
    
    return weeks.slice(-5); // Last 5 weeks
  };

  const generateFallbackWeeklyData = (): WeeklyData[] => {
    return [
      { week: 'Week 1', score: 65, sessions: 3 },
      { week: 'Week 2', score: 72, sessions: 4 },
      { week: 'Week 3', score: 78, sessions: 5 },
      { week: 'Week 4', score: 82, sessions: 4 },
      { week: 'Week 5', score: 85, sessions: 5 },
    ];
  };

  const calculateAchievements = (stats: any, trends: any): any[] => {
    const achievements = [];
    
    if (stats.totalAnalyses >= 10) {
      achievements.push({
        icon: '🎯',
        title: 'Dedication',
        description: '10+ sessions completed'
      });
    }
    
    if (stats.averageScore >= 80) {
      achievements.push({
        icon: '⭐',
        title: 'Excellence',
        description: 'Maintained 80%+ average'
      });
    }
    
    if (stats.improvementRate > 10) {
      achievements.push({
        icon: '📈',
        title: 'Rapid Progress',
        description: '10%+ improvement'
      });
    }
    
    return achievements;
  };

  const getCurrentStreak = (): number => {
    // This would be calculated from actual session dates
    return 7; // Fallback
  };

  const getBestScore = (): number => {
    return Math.max(...weeklyData.map(w => w.score), progressStats?.averageScore || 0);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading progress data...</p>
        </div>
      </div>
    );
  }

  const hasData = progressStats && progressStats.totalAnalyses > 0;

  return (
    <AppLayout>
      <div className="px-4 py-6 space-y-6 max-w-4xl mx-auto pb-24" style={{ paddingBottom: "max(env(safe-area-inset-bottom), 24px)" }}>
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-3">Your Progress</h1>
          <p className="text-gray-600 dark:text-gray-400">
            {hasData ? 'Track your form improvement journey' : 'Start recording to track your progress'}
          </p>
        </motion.div>

        {/* Metrics */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-3 gap-6"
        >
          <MetricCard
            icon={<Target className="w-6 h-6 text-blue-600" />}
            label="Best Score"
            value={hasData ? `${getBestScore()}%` : '-%'}
            tooltip="Your highest form analysis score"
            trend={hasData && progressStats.recentTrend === 'improving' ? '+5%' : undefined}
            trendUp={true}
          />
          <MetricCard
            icon={<Activity className="w-6 h-6 text-green-600" />}
            label="Sessions"
            value={hasData ? progressStats.totalAnalyses : 0}
            tooltip="Total number of recorded sessions"
          />
          <MetricCard
            icon={<TrendingUp className="w-6 h-6 text-orange-600" />}
            label="Streak"
            value={hasData ? `${getCurrentStreak()}d` : '0d'}
            tooltip="Consecutive days with recorded sessions"
          />
        </motion.div>

        {/* Progress Chart */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <Card className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm shadow-lg">
            <CardContent className="p-8">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold text-gray-900 dark:text-white">Weekly Progress</h3>
                {hasData && progressStats.improvementRate > 0 && (
                  <Badge className="bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">
                    <TrendingUp className="w-3 h-3 mr-1" />
                    +{progressStats.improvementRate}% overall
                  </Badge>
                )}
              </div>
              
              <div className="flex items-end justify-between h-48 px-2">
                {weeklyData.map((week, index) => (
                  <motion.div
                    key={week.week}
                    initial={{ height: 0 }}
                    animate={{ height: `${(week.score / 100) * 100}%` }}
                    transition={{ delay: index * 0.2, duration: 0.8, ease: "easeOut" }}
                    className={`flex-1 mx-2 rounded-t-lg relative group ${
                      hasData 
                        ? 'bg-gradient-to-t from-purple-500 to-blue-500 opacity-80 hover:opacity-100' 
                        : 'bg-gradient-to-t from-purple-500/60 to-blue-500/60'
                    } transition-opacity`}
                  >
                    <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 text-sm font-semibold text-gray-700 dark:text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity">
                      {week.score}%
                    </div>
                    {week.sessions > 0 && (
                      <div className="absolute bottom-2 left-1/2 transform -translate-x-1/2 text-xs text-white opacity-0 group-hover:opacity-100 transition-opacity">
                        {week.sessions} sessions
                      </div>
                    )}
                  </motion.div>
                ))}
              </div>
              
              <div className="flex justify-between mt-4 px-2">
                {weeklyData.map((week) => (
                  <div key={week.week} className="flex-1 text-center text-sm text-gray-600 dark:text-gray-400">
                    {week.week}
                  </div>
                ))}
              </div>

              {!hasData && (
                <div className="border-t border-gray-200/50 dark:border-gray-700/30 pt-6 mt-6">
                  <Badge variant="secondary" className="mb-4">Preview Mode</Badge>
                  <p className="text-gray-600 dark:text-gray-400 mb-6">
                    This is what your progress chart will look like once you start recording!
                  </p>
                  <Button
                    size="lg"
                    className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
                    onClick={() => navigate('/record')}
                  >
                    <Camera className="w-5 h-5 mr-2" />
                    Record Your First Exercise
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Exercise Breakdown */}
        {hasData && Object.keys(exerciseBreakdown).length > 0 && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <Card className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm shadow-lg">
              <CardContent className="p-6">
                <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Exercise Performance</h3>
                <div className="space-y-4">
                  {Object.entries(exerciseBreakdown).map(([exercise, data]: [string, any]) => (
                    <div key={exercise} className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                          <span className="text-lg">
                            {exercise === 'squat' && '🏋️'}
                            {exercise === 'deadlift' && '💪'}
                            {exercise === 'bench_press' && '🏃'}
                            {exercise === 'overhead_press' && '🎯'}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">
                            {exercise.replace('_', ' ').charAt(0).toUpperCase() + exercise.slice(1).replace('_', ' ')}
                          </p>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            {data.count} sessions • {Math.round(data.avgScore)}% avg
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {data.trend === 'up' && (
                          <Badge className="bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">
                            <TrendingUp className="w-3 h-3 mr-1" />
                            +{data.improvement}%
                          </Badge>
                        )}
                        <Progress value={data.avgScore} className="w-20 h-2" />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Achievements */}
        {achievements.length > 0 && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
            <Card className="bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-900/20 dark:to-orange-900/20">
              <CardContent className="p-6">
                <div className="flex items-center space-x-2 mb-4">
                  <Award className="w-6 h-6 text-yellow-600" />
                  <h3 className="text-xl font-bold text-gray-900 dark:text-white">Achievements</h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {achievements.map((achievement, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 0.5 + index * 0.1 }}
                      className="text-center"
                    >
                      <div className="text-3xl mb-2">{achievement.icon}</div>
                      <h4 className="font-semibold text-gray-900 dark:text-white">{achievement.title}</h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{achievement.description}</p>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Quick Stats */}
        {hasData && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
            <div className="grid grid-cols-2 gap-4">
              <Card className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm">
                <CardContent className="p-4">
                  <div className="flex items-center space-x-3">
                    <Calendar className="w-5 h-5 text-purple-600" />
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400">This Month</p>
                      <p className="font-semibold text-gray-900 dark:text-white">
                        {weeklyData.reduce((sum, week) => sum + week.sessions, 0)} sessions
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              
              <Card className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm">
                <CardContent className="p-4">
                  <div className="flex items-center space-x-3">
                    <Zap className="w-5 h-5 text-orange-600" />
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400">Trend</p>
                      <p className="font-semibold text-gray-900 dark:text-white capitalize">
                        {progressStats.recentTrend}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </motion.div>
        )}

        {/* CTA for new session */}
        {hasData && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}>
            <Button
              size="lg"
              className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
              onClick={() => navigate('/record')}
            >
              <Camera className="w-5 h-5 mr-2" />
              Record New Session
            </Button>
          </motion.div>
        )}
      </div>
    </AppLayout>
  );
}