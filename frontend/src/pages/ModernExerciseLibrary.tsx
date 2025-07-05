import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';

const ModernExerciseLibrary: React.FC = () => {
  const exercises = [
    {
      id: '1',
      name: 'Squat',
      category: 'Lower Body',
      difficulty: 'Beginner',
      description: 'A fundamental lower body exercise that targets quads, glutes, and hamstrings.'
    },
    {
      id: '2',
      name: 'Push-up',
      category: 'Upper Body',
      difficulty: 'Beginner',
      description: 'A classic bodyweight exercise for chest, shoulders, and triceps.'
    },
    {
      id: '3',
      name: 'Deadlift',
      category: 'Full Body',
      difficulty: 'Intermediate',
      description: 'A compound movement that works the entire posterior chain.'
    }
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-4">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold">Exercise Library</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Explore exercises and learn proper form techniques
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {exercises.map((exercise) => (
            <Card key={exercise.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <CardTitle className="text-lg">{exercise.name}</CardTitle>
                  <Badge variant="secondary">{exercise.difficulty}</Badge>
                </div>
                <CardDescription>{exercise.category}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {exercise.description}
                </p>
                <div className="flex space-x-2">
                  <Button size="sm" className="flex-1">
                    Learn Form
                  </Button>
                  <Button variant="outline" size="sm" className="flex-1">
                    Practice
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ModernExerciseLibrary;