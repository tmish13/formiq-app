import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import {
  ArrowLeft,
  Calendar,
  TrendingUp,
  Eye,
  Plus,
  Filter,
  Search,
  LoaderIcon,
  Target,
} from 'lucide-react';
import { Input } from '../components/ui/input';
import { useToast } from '../hooks/use-toast';
import AppLayout from '../components/layout/AppLayout';

// Import our backend services
import { formCheckService } from '../services/formCheckService';
import { FormCheck, ExerciseType } from '../types/formCheck';

export default function AnalysisListPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [formChecks, setFormChecks] = useState<FormCheck[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedExercise, setSelectedExercise] = useState<ExerciseType | 'all'>('all');

  useEffect(() => {
    loadFormChecks();
  }, []);

  const loadFormChecks = async () => {
    try {
      setLoading(true);
      const formCheckData = await formCheckService.getFormChecks();
      setFormChecks(formCheckData);
    } catch (error) {
      console.error('Failed to load form checks:', error);
      toast({
        title: 'Loading Error',
        description: 'Failed to load analysis history.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600 bg-green-50';
    if (score >= 80) return 'text-blue-600 bg-blue-50';
    if (score >= 60) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-500 text-white">Completed</Badge>;
      case 'processing':
        return <Badge className="bg-blue-500 text-white">Processing</Badge>;
      case 'failed':
        return <Badge className="bg-red-500 text-white">Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const filteredFormChecks = formChecks.filter((formCheck) => {
    const matchesSearch = 
      formCheck.exercise_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (formCheck.created_at && new Date(formCheck.created_at).toLocaleDateString().includes(searchTerm));
    
    const matchesExercise = selectedExercise === 'all' || formCheck.exercise_type === selectedExercise;
    
    return matchesSearch && matchesExercise;
  });

  const exerciseTypes: (ExerciseType | 'all')[] = ['all', 'squat', 'deadlift', 'bench_press', 'overhead_press'];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <LoaderIcon className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-gray-600 dark:text-gray-400">Loading analyses...</p>
        </div>
      </div>
    );
  }

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
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Analysis History</h1>
          <Button 
            size="sm"
            onClick={() => navigate('/record')}
          >
            <Plus className="w-4 h-4 mr-2" />
            New
          </Button>
        </div>
      </div>

      <div className="px-4 py-6 space-y-6">
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

          <div className="flex items-center space-x-2 overflow-x-auto pb-2">
            <Filter className="w-4 h-4 text-gray-500 flex-shrink-0" />
            {exerciseTypes.map((type) => (
              <Button
                key={type}
                variant={selectedExercise === type ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedExercise(type)}
                className="flex-shrink-0"
              >
                {type === 'all' ? 'All' : type.replace('_', ' ').charAt(0).toUpperCase() + type.slice(1).replace('_', ' ')}
              </Button>
            ))}
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
                  {formChecks.filter(fc => fc.status === 'completed').length}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Completed</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {Math.round(formChecks
                    .filter(fc => fc.score && fc.status === 'completed')
                    .reduce((sum, fc) => sum + (fc.score || 0), 0) / 
                    Math.max(1, formChecks.filter(fc => fc.score && fc.status === 'completed').length)
                  )}%
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Avg Score</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {new Set(formChecks.map(fc => fc.exercise_type)).size}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Exercises</div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Analysis List */}
        <div className="space-y-3">
          {filteredFormChecks.length === 0 ? (
            <Card>
              <CardContent className="p-8 text-center">
                <Target className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  {formChecks.length === 0 ? 'No Analyses Yet' : 'No Matching Analyses'}
                </h3>
                <p className="text-gray-600 dark:text-gray-400 mb-4">
                  {formChecks.length === 0 
                    ? 'Start your form analysis journey by recording your first exercise!'
                    : 'Try adjusting your search or filter criteria.'
                  }
                </p>
                <Button onClick={() => navigate('/record')}>
                  <Plus className="w-4 h-4 mr-2" />
                  Record First Analysis
                </Button>
              </CardContent>
            </Card>
          ) : (
            filteredFormChecks
              .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
              .map((formCheck) => (
                <Card 
                  key={formCheck.id} 
                  className="cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => navigate(`/analysis/${formCheck.id}`)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center space-x-3">
                        <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                          <span className="text-2xl">
                            {formCheck.exercise_type === 'squat' && '🏋️'}
                            {formCheck.exercise_type === 'deadlift' && '💪'}
                            {formCheck.exercise_type === 'bench_press' && '🏃'}
                            {formCheck.exercise_type === 'overhead_press' && '🎯'}
                            {!['squat', 'deadlift', 'bench_press', 'overhead_press'].includes(formCheck.exercise_type) && '🏃'}
                          </span>
                        </div>
                        <div>
                          <h3 className="font-semibold text-gray-900 dark:text-white">
                            {formCheck.exercise_type.replace('_', ' ').charAt(0).toUpperCase() + 
                             formCheck.exercise_type.slice(1).replace('_', ' ')} Analysis
                          </h3>
                          <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
                            <Calendar className="w-3 h-3" />
                            <span>
                              {new Date(formCheck.created_at).toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric',
                                hour: 'numeric',
                                minute: '2-digit',
                              })}
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="text-right space-y-1">
                        {getStatusBadge(formCheck.status)}
                        {formCheck.score && formCheck.status === 'completed' && (
                          <div className={`text-sm font-bold px-2 py-1 rounded ${getScoreColor(formCheck.score)}`}>
                            {formCheck.score}%
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Progress indicators for ML scores */}
                    {formCheck.posture_score !== undefined && formCheck.stability_score !== undefined && formCheck.depth_score !== undefined && (
                      <div className="grid grid-cols-3 gap-2 mt-3">
                        <div className="text-center">
                          <div className="text-xs text-gray-500 dark:text-gray-400">Posture</div>
                          <div className="text-sm font-semibold text-blue-600">{Math.round(formCheck.posture_score * 100)}%</div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs text-gray-500 dark:text-gray-400">Stability</div>
                          <div className="text-sm font-semibold text-green-600">{Math.round(formCheck.stability_score * 100)}%</div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs text-gray-500 dark:text-gray-400">Depth</div>
                          <div className="text-sm font-semibold text-purple-600">{Math.round(formCheck.depth_score * 100)}%</div>
                        </div>
                      </div>
                    )}

                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                      <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
                        <Eye className="w-3 h-3" />
                        <span>View Details</span>
                      </div>
                      {formCheck.status === 'completed' && formCheck.score && (
                        <div className="flex items-center space-x-1 text-sm text-green-600">
                          <TrendingUp className="w-3 h-3" />
                          <span>Analyzed</span>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))
          )}
        </div>

        {/* Load More Button (if needed for pagination) */}
        {filteredFormChecks.length > 0 && filteredFormChecks.length >= 20 && (
          <div className="text-center">
            <Button variant="outline" onClick={loadFormChecks}>
              Load More Analyses
            </Button>
          </div>
        )}
      </div>
      </div>
    </AppLayout>
  );
}