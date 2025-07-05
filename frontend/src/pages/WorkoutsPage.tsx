import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Play, Plus, Clock, Target, Flame, CheckCircle, Calendar, Search, Filter, Dumbbell, Timer } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Input } from '../components/ui/input';
import { useToast } from '../hooks/use-toast';
import AppLayout from '../components/layout/AppLayout';
import { useNavigate } from 'react-router-dom';

const workoutTemplates = [
  {
    id: 1,
    name: 'Upper Body Strength',
    duration: '45 min',
    exercises: 6,
    difficulty: 'Intermediate',
    category: 'Strength',
    description: 'Build upper body muscle and strength',
    exercises_list: ['Bench Press', 'Pull-ups', 'Overhead Press', 'Rows', 'Dips', 'Curls'],
  },
  {
    id: 2,
    name: 'Lower Body Power',
    duration: '40 min',
    exercises: 5,
    difficulty: 'Advanced',
    category: 'Power',
    description: 'Explosive lower body movements',
    exercises_list: ['Squats', 'Deadlifts', 'Jump Squats', 'Lunges', 'Hip Thrusts'],
  },
  {
    id: 3,
    name: 'Full Body HIIT',
    duration: '30 min',
    exercises: 8,
    difficulty: 'Beginner',
    category: 'Cardio',
    description: 'High-intensity full body workout',
    exercises_list: [
      'Burpees',
      'Mountain Climbers',
      'Push-ups',
      'Squats',
      'Plank',
      'Jumping Jacks',
      'Lunges',
      'High Knees',
    ],
  },
  {
    id: 4,
    name: 'Core & Stability',
    duration: '25 min',
    exercises: 7,
    difficulty: 'Intermediate',
    category: 'Core',
    description: 'Strengthen your core and improve stability',
    exercises_list: ['Plank', 'Dead Bug', 'Bird Dog', 'Russian Twists', 'Hollow Hold', 'Side Plank', 'Glute Bridge'],
  },
  {
    id: 5,
    name: 'Flexibility & Mobility',
    duration: '20 min',
    exercises: 10,
    difficulty: 'Beginner',
    category: 'Mobility',
    description: 'Improve range of motion and flexibility',
    exercises_list: ['Hip Circles', 'Shoulder Rolls', 'Hamstring Stretch', 'Quad Stretch', 'Calf Stretch'],
  },
  {
    id: 6,
    name: 'Push Day',
    duration: '50 min',
    exercises: 7,
    difficulty: 'Advanced',
    category: 'Strength',
    description: 'Focus on pushing movements',
    exercises_list: ['Bench Press', 'Overhead Press', 'Dips', 'Push-ups', 'Lateral Raises', 'Tricep Extensions'],
  },
];

const activeWorkout = {
  name: 'Upper Body Strength',
  currentExercise: 2,
  totalExercises: 6,
  timeElapsed: '12:34',
  exercises: [
    { name: 'Bench Press', sets: 4, reps: '8-10', completed: true, weight: '185 lbs' },
    { name: 'Pull-ups', sets: 3, reps: '6-8', completed: true, weight: 'Body weight' },
    { name: 'Overhead Press', sets: 4, reps: '8-10', completed: false, weight: '135 lbs', current: true },
    { name: 'Bent-over Rows', sets: 4, reps: '8-10', completed: false, weight: '155 lbs' },
    { name: 'Dips', sets: 3, reps: '10-12', completed: false, weight: 'Body weight' },
    { name: 'Bicep Curls', sets: 3, reps: '12-15', completed: false, weight: '35 lbs' },
  ],
};

const recentWorkouts = [
  { id: 1, name: 'Upper Body Strength', date: '2024-01-14', duration: '47 min', formChecks: 3 },
  { id: 2, name: 'Lower Body Power', date: '2024-01-12', duration: '42 min', formChecks: 2 },
  { id: 3, name: 'Full Body HIIT', date: '2024-01-10', duration: '28 min', formChecks: 4 },
  { id: 4, name: 'Core & Stability', date: '2024-01-08', duration: '23 min', formChecks: 2 },
  { id: 5, name: 'Push Day', date: '2024-01-06', duration: '52 min', formChecks: 5 },
];

export default function WorkoutsPage() {
  const [activeTab, setActiveTab] = useState('browse');
  const [searchQuery, setSearchQuery] = useState('');
  const [hasActiveWorkout, setHasActiveWorkout] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'Beginner':
        return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400';
      case 'Intermediate':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400';
      case 'Advanced':
        return 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'Strength':
        return <Dumbbell className="w-4 h-4" />;
      case 'Power':
        return <Flame className="w-4 h-4" />;
      case 'Cardio':
        return <Timer className="w-4 h-4" />;
      case 'Core':
        return <Target className="w-4 h-4" />;
      case 'Mobility':
        return <Target className="w-4 h-4" />;
      default:
        return <Dumbbell className="w-4 h-4" />;
    }
  };

  const handleStartWorkout = (workoutName: string) => {
    setHasActiveWorkout(true);
    toast({
      title: '🏋️ Workout Started!',
      description: `Started ${workoutName}. Good luck with your training!`,
      duration: 3000,
    });
  };

  const handleFormCheck = () => {
    navigate('/record');
  };

  const handleCreateWorkout = () => {
    toast({
      title: 'Coming Soon',
      description: 'Custom workout builder will be available in a future update!',
      duration: 2000,
    });
  };

  const filteredWorkouts = workoutTemplates.filter(workout =>
    workout.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    workout.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
    workout.exercises_list.some(exercise => 
      exercise.toLowerCase().includes(searchQuery.toLowerCase())
    )
  );

  return (
    <AppLayout>
      <div className="bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 pb-24" style={{ paddingBottom: "max(env(safe-area-inset-bottom), 24px)" }}>
      {/* Header */}
      <motion.header 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white dark:bg-gray-800 shadow-sm border-b"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">Workouts</h1>
            </div>
            <div className="flex items-center space-x-4">
              {hasActiveWorkout && (
                <Badge variant="secondary" className="bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">
                  <Play className="w-3 h-3 mr-1" />
                  Workout in progress
                </Badge>
              )}
              <Button size="sm" onClick={handleCreateWorkout}>
                <Plus className="w-4 h-4 mr-2" />
                Create Workout
              </Button>
            </div>
          </div>
        </div>
      </motion.header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {hasActiveWorkout ? (
          /* Active Workout View */
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Workout Header */}
            <Card className="bg-gradient-to-r from-blue-500 to-blue-600 text-white border-0">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-2xl font-bold mb-2">{activeWorkout.name}</h2>
                    <div className="flex items-center space-x-4 text-blue-100">
                      <div className="flex items-center space-x-1">
                        <Clock className="w-4 h-4" />
                        <span>{activeWorkout.timeElapsed}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <Target className="w-4 h-4" />
                        <span>
                          {activeWorkout.currentExercise}/{activeWorkout.totalExercises} exercises
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <Progress
                      value={(activeWorkout.currentExercise / activeWorkout.totalExercises) * 100}
                      className="w-32 mb-2"
                    />
                    <p className="text-sm text-blue-100">
                      {Math.round((activeWorkout.currentExercise / activeWorkout.totalExercises) * 100)}% Complete
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Exercise List */}
            <div className="grid grid-cols-1 gap-4">
              {activeWorkout.exercises.map((exercise, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <Card
                    className={`${exercise.current ? 'ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/20' : ''} ${
                      exercise.completed ? 'opacity-75' : ''
                    }`}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <div
                            className={`w-8 h-8 rounded-full flex items-center justify-center ${
                              exercise.completed
                                ? 'bg-green-500'
                                : exercise.current
                                  ? 'bg-blue-500'
                                  : 'bg-gray-200 dark:bg-gray-700'
                            }`}
                          >
                            {exercise.completed ? (
                              <CheckCircle className="w-5 h-5 text-white" />
                            ) : (
                              <span
                                className={`text-sm font-medium ${
                                  exercise.current ? 'text-white' : 'text-gray-600 dark:text-gray-400'
                                }`}
                              >
                                {index + 1}
                              </span>
                            )}
                          </div>
                          <div>
                            <h3
                              className={`font-medium ${
                                exercise.current ? 'text-blue-600 dark:text-blue-400' : 'text-gray-900 dark:text-white'
                              }`}
                            >
                              {exercise.name}
                            </h3>
                            <p className="text-sm text-gray-500 dark:text-gray-400">
                              {exercise.sets} sets × {exercise.reps} reps • {exercise.weight}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          {exercise.current && (
                            <>
                              <Button size="sm" variant="outline" onClick={handleFormCheck}>
                                Form Check
                              </Button>
                              <Button size="sm">Complete Set</Button>
                            </>
                          )}
                          {exercise.completed && (
                            <Badge variant="secondary" className="bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">
                              Completed
                            </Badge>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>

            {/* Workout Controls */}
            <div className="flex space-x-4">
              <Button
                variant="outline"
                className="flex-1 bg-transparent"
                onClick={() => {
                  setHasActiveWorkout(false);
                  toast({
                    title: '⏸️ Workout Paused',
                    description: 'Your workout has been paused. You can resume anytime!',
                    duration: 2000,
                  });
                }}
              >
                Pause Workout
              </Button>
              <Button
                className="flex-1"
                onClick={() => {
                  setHasActiveWorkout(false);
                  toast({
                    title: '🎉 Workout Complete!',
                    description: 'Great job! Your workout has been saved to your history.',
                    duration: 3000,
                  });
                }}
              >
                Finish Workout
              </Button>
            </div>
          </motion.div>
        ) : (
          /* Workout Browser */
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="browse">Browse Workouts</TabsTrigger>
                <TabsTrigger value="history">Workout History</TabsTrigger>
                <TabsTrigger value="custom">My Workouts</TabsTrigger>
              </TabsList>

              <TabsContent value="browse" className="space-y-6">
                {/* Search and Filters */}
                <div className="flex space-x-4">
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                    <Input
                      placeholder="Search workouts..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                  <Button variant="outline" onClick={() => toast({ title: 'Coming Soon', description: 'Advanced filters coming soon!', duration: 2000 })}>
                    <Filter className="w-4 h-4 mr-2" />
                    Filters
                  </Button>
                </div>

                {/* Workout Templates */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {filteredWorkouts.map((workout, index) => (
                    <motion.div
                      key={workout.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                    >
                      <Card className="hover:shadow-lg transition-shadow h-full">
                        <CardHeader>
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <CardTitle className="flex items-center space-x-2">
                                {getCategoryIcon(workout.category)}
                                <span>{workout.name}</span>
                              </CardTitle>
                              <CardDescription className="mt-1">{workout.description}</CardDescription>
                            </div>
                            <Badge className={getDifficultyColor(workout.difficulty)}>{workout.difficulty}</Badge>
                          </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <div className="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                            <div className="flex items-center space-x-1">
                              <Clock className="w-4 h-4" />
                              <span>{workout.duration}</span>
                            </div>
                            <div className="flex items-center space-x-1">
                              <Target className="w-4 h-4" />
                              <span>{workout.exercises} exercises</span>
                            </div>
                            <Badge variant="outline">{workout.category}</Badge>
                          </div>

                          <div>
                            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Exercises:</p>
                            <div className="flex flex-wrap gap-1">
                              {workout.exercises_list.slice(0, 4).map((exercise, idx) => (
                                <Badge key={idx} variant="secondary" className="text-xs">
                                  {exercise}
                                </Badge>
                              ))}
                              {workout.exercises_list.length > 4 && (
                                <Badge variant="secondary" className="text-xs">
                                  +{workout.exercises_list.length - 4} more
                                </Badge>
                              )}
                            </div>
                          </div>

                          <div className="flex space-x-2 pt-2">
                            <Button className="flex-1" onClick={() => handleStartWorkout(workout.name)}>
                              <Play className="w-4 h-4 mr-2" />
                              Start Workout
                            </Button>
                            <Button variant="outline" size="sm" onClick={() => toast({ title: 'Preview', description: `Viewing details for ${workout.name}`, duration: 2000 })}>
                              Preview
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    </motion.div>
                  ))}
                </div>

                {filteredWorkouts.length === 0 && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-12">
                    <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                      <Search className="w-8 h-8 text-gray-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">No workouts found</h3>
                    <p className="text-gray-600 dark:text-gray-400">Try adjusting your search terms</p>
                  </motion.div>
                )}
              </TabsContent>

              <TabsContent value="history" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Calendar className="w-5 h-5 text-blue-600" />
                      <span>Recent Workouts</span>
                    </CardTitle>
                    <CardDescription>Your workout history and performance</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {recentWorkouts.map((workout, index) => (
                        <motion.div
                          key={workout.id}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: index * 0.1 }}
                          className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg"
                        >
                          <div className="flex items-center space-x-4">
                            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
                              <CheckCircle className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                            </div>
                            <div>
                              <h4 className="font-medium text-gray-900 dark:text-white">{workout.name}</h4>
                              <p className="text-sm text-gray-500 dark:text-gray-400">
                                {workout.date} • {workout.duration} • {workout.formChecks} form checks
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center space-x-2">
                            <Button variant="ghost" size="sm" onClick={() => toast({ title: 'Workout Details', description: `Viewing details for ${workout.name}`, duration: 2000 })}>
                              View Details
                            </Button>
                            <Button variant="outline" size="sm" onClick={() => handleStartWorkout(workout.name)}>
                              Repeat
                            </Button>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="custom" className="space-y-6">
                <Card>
                  <CardContent className="p-8 text-center">
                    <motion.div
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 0.2 }}
                    >
                      <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Plus className="w-8 h-8 text-gray-400" />
                      </div>
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                        Create Your First Custom Workout
                      </h3>
                      <p className="text-gray-600 dark:text-gray-400 mb-6">
                        Build personalized workouts tailored to your goals and preferences
                      </p>
                      <Button onClick={handleCreateWorkout}>
                        <Plus className="w-4 h-4 mr-2" />
                        Create Custom Workout
                      </Button>
                    </motion.div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </motion.div>
        )}
      </div>
      </div>
    </AppLayout>
  );
}