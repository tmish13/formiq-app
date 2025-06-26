import React, { useState, useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  LinearProgress,
  Button,
  IconButton,
  Tooltip,
  Alert,
  Avatar,
  Divider,
  Grid,
  Rating,
  Badge
} from '@mui/material';
import {
  ExpandMore,
  Warning,
  CheckCircle,
  Error,
  Info,
  TrendingUp,
  Psychology,
  AutoFixHigh,
  VideoLibrary,
  PlayArrow,
  Lightbulb,
  Timeline,
  School,
  Star,
  ThumbUp,
  ThumbDown
} from '@mui/icons-material';
import { FormCheck } from '../../types/formCheck';
import { MLScores, PoseIssue } from '../../types/ml';

interface FeedbackItem {
  id: string;
  type: 'correction' | 'improvement' | 'praise' | 'warning';
  category: 'posture' | 'stability' | 'depth' | 'tempo' | 'safety';
  title: string;
  description: string;
  severity: 'low' | 'medium' | 'high';
  timestamp?: number;
  suggestions: string[];
  videoReference?: string;
  aiGenerated: boolean;
  confidence: number;
}

interface PersonalizedRecommendation {
  id: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  category: 'technique' | 'mobility' | 'strength' | 'progression';
  estimatedImpact: number; // 1-10 scale
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  timeToSee: string;
  resources: Array<{
    type: 'video' | 'article' | 'exercise';
    title: string;
    url: string;
  }>;
}

interface AdvancedFeedbackPreviewProps {
  formCheck: FormCheck;
  mlScores?: MLScores;
  poseIssues?: PoseIssue[];
  onFeedbackRating?: (feedbackId: string, rating: number) => void;
  onApplyRecommendation?: (recommendationId: string) => void;
}

const FEEDBACK_COLORS = {
  correction: '#FF5722',
  improvement: '#FF9500',
  praise: '#4CAF50',
  warning: '#F44336'
};

const SEVERITY_COLORS = {
  low: '#4CAF50',
  medium: '#FF9500',
  high: '#F44336'
};

const PRIORITY_COLORS = {
  high: '#F44336',
  medium: '#FF9500',
  low: '#4CAF50'
};

export const AdvancedFeedbackPreview: React.FC<AdvancedFeedbackPreviewProps> = ({
  formCheck,
  mlScores,
  poseIssues = [],
  onFeedbackRating,
  onApplyRecommendation
}) => {
  const [expandedSections, setExpandedSections] = useState<string[]>(['feedback']);
  const [feedbackRatings, setFeedbackRatings] = useState<Record<string, number>>({});

  // Generate AI-powered feedback items based on ML scores and pose issues
  const feedbackItems = useMemo((): FeedbackItem[] => {
    const items: FeedbackItem[] = [];

    // Generate feedback from ML scores
    if (mlScores) {
      // Posture feedback
      if (mlScores.posture_score < 70) {
        items.push({
          id: 'posture-correction',
          type: 'correction',
          category: 'posture',
          title: 'Posture Alignment Needs Attention',
          description: `Your posture score of ${Math.round(mlScores.posture_score)}% indicates some alignment issues. Focus on maintaining a neutral spine and proper shoulder positioning.`,
          severity: mlScores.posture_score < 50 ? 'high' : 'medium',
          suggestions: [
            'Keep your chest up and shoulders back',
            'Engage your core muscles throughout the movement',
            'Practice wall slides to improve shoulder mobility',
            'Consider posture-specific warm-up exercises'
          ],
          videoReference: '/videos/posture-correction-techniques',
          aiGenerated: true,
          confidence: mlScores.confidence || 0.8
        });
      } else if (mlScores.posture_score > 85) {
        items.push({
          id: 'posture-praise',
          type: 'praise',
          category: 'posture',
          title: 'Excellent Posture Control',
          description: `Outstanding posture with a score of ${Math.round(mlScores.posture_score)}%! Your alignment is on point.`,
          severity: 'low',
          suggestions: [
            'Maintain this excellent posture consistency',
            'Try increasing the challenge while keeping form',
            'Help others with posture tips'
          ],
          aiGenerated: true,
          confidence: mlScores.confidence || 0.9
        });
      }

      // Stability feedback
      if (mlScores.stability_score < 70) {
        items.push({
          id: 'stability-improvement',
          type: 'improvement',
          category: 'stability',
          title: 'Stability Can Be Enhanced',
          description: `Your stability score of ${Math.round(mlScores.stability_score)}% suggests room for improvement in balance and control.`,
          severity: 'medium',
          suggestions: [
            'Practice single-leg balance exercises',
            'Strengthen your core and stabilizer muscles',
            'Focus on controlled, deliberate movements',
            'Consider stability ball training'
          ],
          videoReference: '/videos/stability-training',
          aiGenerated: true,
          confidence: mlScores.confidence || 0.8
        });
      }

      // Depth feedback
      if (mlScores.depth_score < 60) {
        items.push({
          id: 'depth-warning',
          type: 'warning',
          category: 'depth',
          title: 'Range of Motion Limitation',
          description: `Your depth score of ${Math.round(mlScores.depth_score)}% indicates limited range of motion. This could affect exercise effectiveness.`,
          severity: 'high',
          suggestions: [
            'Work on mobility and flexibility daily',
            'Perform dynamic warm-up exercises',
            'Consider seeing a physical therapist',
            'Gradually increase range of motion'
          ],
          videoReference: '/videos/mobility-exercises',
          aiGenerated: true,
          confidence: mlScores.confidence || 0.8
        });
      }
    }

    // Add specific pose issue feedback
    poseIssues.forEach((issue, index) => {
      items.push({
        id: `pose-issue-${index}`,
        type: issue.severity === 'high' ? 'warning' : 'correction',
        category: issue.type,
        title: `${issue.type.charAt(0).toUpperCase() + issue.type.slice(1)} Issue Detected`,
        description: issue.description,
        severity: issue.severity,
        timestamp: issue.timestamp,
        suggestions: issue.suggestions,
        aiGenerated: true,
        confidence: 0.85
      });
    });

    return items;
  }, [mlScores, poseIssues]);

  // Generate personalized recommendations
  const recommendations = useMemo((): PersonalizedRecommendation[] => {
    const recs: PersonalizedRecommendation[] = [];

    if (mlScores) {
      // Weak area recommendations
      const weakestScore = Math.min(mlScores.posture_score, mlScores.stability_score, mlScores.depth_score);
      
      if (mlScores.posture_score === weakestScore) {
        recs.push({
          id: 'posture-improvement-plan',
          title: 'Posture Enhancement Program',
          description: 'A targeted program to improve your posture alignment and reduce compensation patterns.',
          priority: 'high',
          category: 'technique',
          estimatedImpact: 8,
          difficulty: 'beginner',
          timeToSee: '2-3 weeks',
          resources: [
            { type: 'video', title: 'Daily Posture Routine', url: '/videos/posture-routine' },
            { type: 'article', title: 'Understanding Posture Mechanics', url: '/articles/posture-guide' },
            { type: 'exercise', title: 'Wall Slide Exercise', url: '/exercises/wall-slides' }
          ]
        });
      }

      if (mlScores.stability_score === weakestScore) {
        recs.push({
          id: 'stability-training-plan',
          title: 'Core Stability Enhancement',
          description: 'Build a stronger, more stable core to improve your movement quality and control.',
          priority: 'high',
          category: 'strength',
          estimatedImpact: 7,
          difficulty: 'intermediate',
          timeToSee: '3-4 weeks',
          resources: [
            { type: 'video', title: 'Core Stability Workout', url: '/videos/core-stability' },
            { type: 'exercise', title: 'Plank Progressions', url: '/exercises/plank-progressions' }
          ]
        });
      }

      if (mlScores.depth_score === weakestScore) {
        recs.push({
          id: 'mobility-improvement-plan',
          title: 'Mobility & Flexibility Program',
          description: 'Improve your range of motion and movement quality through targeted mobility work.',
          priority: 'high',
          category: 'mobility',
          estimatedImpact: 9,
          difficulty: 'beginner',
          timeToSee: '1-2 weeks',
          resources: [
            { type: 'video', title: 'Daily Mobility Routine', url: '/videos/mobility-routine' },
            { type: 'article', title: 'Mobility vs Flexibility Guide', url: '/articles/mobility-guide' }
          ]
        });
      }
    }

    // Exercise-specific recommendations
    if (formCheck.exercise_type === 'squat') {
      recs.push({
        id: 'squat-progression',
        title: 'Squat Technique Refinement',
        description: 'Advanced squat techniques to take your form to the next level.',
        priority: 'medium',
        category: 'progression',
        estimatedImpact: 6,
        difficulty: 'intermediate',
        timeToSee: '2-3 weeks',
        resources: [
          { type: 'video', title: 'Advanced Squat Techniques', url: '/videos/advanced-squats' },
          { type: 'exercise', title: 'Goblet Squat to Back Squat Progression', url: '/exercises/squat-progression' }
        ]
      });
    }

    return recs.sort((a, b) => {
      const priorityOrder = { high: 3, medium: 2, low: 1 };
      return priorityOrder[b.priority] - priorityOrder[a.priority];
    });
  }, [mlScores, formCheck.exercise_type]);

  const handleSectionToggle = (section: string) => {
    setExpandedSections(prev => 
      prev.includes(section) 
        ? prev.filter(s => s !== section)
        : [...prev, section]
    );
  };

  const handleFeedbackRating = (feedbackId: string, rating: number) => {
    setFeedbackRatings(prev => ({ ...prev, [feedbackId]: rating }));
    onFeedbackRating?.(feedbackId, rating);
  };

  const getFeedbackIcon = (type: string) => {
    switch (type) {
      case 'correction': return <AutoFixHigh />;
      case 'improvement': return <TrendingUp />;
      case 'praise': return <CheckCircle />;
      case 'warning': return <Warning />;
      default: return <Info />;
    }
  };

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'high': return <Error color="error" />;
      case 'medium': return <Warning color="warning" />;
      case 'low': return <Info color="info" />;
      default: return <Info />;
    }
  };

  return (
    <Box sx={{ width: '100%' }}>
      {/* AI-Powered Feedback Section */}
      <Accordion 
        expanded={expandedSections.includes('feedback')}
        onChange={() => handleSectionToggle('feedback')}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
            <Psychology color="primary" />
            <Typography variant="h6">AI-Powered Feedback</Typography>
            <Badge badgeContent={feedbackItems.length} color="primary">
              <Chip size="small" label="New" />
            </Badge>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <List>
            {feedbackItems.map((item, index) => (
              <React.Fragment key={item.id}>
                <ListItem sx={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, width: '100%' }}>
                    <Avatar sx={{ bgcolor: FEEDBACK_COLORS[item.type], width: 32, height: 32 }}>
                      {getFeedbackIcon(item.type)}
                    </Avatar>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="subtitle1" fontWeight="medium">
                        {item.title}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
                        <Chip 
                          size="small" 
                          label={item.category} 
                          color="primary" 
                          variant="outlined"
                        />
                        <Chip 
                          size="small" 
                          label={item.severity} 
                          sx={{ 
                            bgcolor: SEVERITY_COLORS[item.severity],
                            color: 'white',
                            fontWeight: 'bold'
                          }}
                        />
                        {item.aiGenerated && (
                          <Chip 
                            size="small" 
                            label={`AI ${Math.round(item.confidence * 100)}%`}
                            color="info"
                            variant="outlined"
                          />
                        )}
                      </Box>
                    </Box>
                  </Box>

                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {item.description}
                  </Typography>

                  {item.suggestions.length > 0 && (
                    <Box sx={{ mb: 2, width: '100%' }}>
                      <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <Lightbulb fontSize="small" />
                        Suggestions:
                      </Typography>
                      <List dense>
                        {item.suggestions.map((suggestion, idx) => (
                          <ListItem key={idx} sx={{ py: 0.5 }}>
                            <ListItemIcon sx={{ minWidth: 32 }}>
                              <CheckCircle fontSize="small" color="success" />
                            </ListItemIcon>
                            <ListItemText primary={suggestion} />
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                  )}

                  {item.videoReference && (
                    <Button
                      startIcon={<PlayArrow />}
                      variant="outlined"
                      size="small"
                      sx={{ mb: 2 }}
                    >
                      Watch Tutorial
                    </Button>
                  )}

                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                    <Typography variant="body2">Was this helpful?</Typography>
                    <Rating
                      size="small"
                      value={feedbackRatings[item.id] || 0}
                      onChange={(_, value) => value && handleFeedbackRating(item.id, value)}
                    />
                    <Box sx={{ ml: 'auto', display: 'flex', gap: 1 }}>
                      <IconButton size="small" color="success">
                        <ThumbUp fontSize="small" />
                      </IconButton>
                      <IconButton size="small" color="error">
                        <ThumbDown fontSize="small" />
                      </IconButton>
                    </Box>
                  </Box>
                </ListItem>
                {index < feedbackItems.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        </AccordionDetails>
      </Accordion>

      {/* Personalized Recommendations Section */}
      <Accordion 
        expanded={expandedSections.includes('recommendations')}
        onChange={() => handleSectionToggle('recommendations')}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <School color="primary" />
            <Typography variant="h6">Personalized Recommendations</Typography>
            <Badge badgeContent={recommendations.length} color="secondary">
              <Star color="action" />
            </Badge>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            {recommendations.map((rec) => (
              <Grid item xs={12} md={6} key={rec.id}>
                <Card variant="outlined">
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      {getPriorityIcon(rec.priority)}
                      <Typography variant="h6" sx={{ flex: 1 }}>
                        {rec.title}
                      </Typography>
                    </Box>

                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {rec.description}
                    </Typography>

                    <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                      <Chip size="small" label={rec.category} color="primary" />
                      <Chip size="small" label={rec.difficulty} />
                      <Chip size="small" label={`Impact: ${rec.estimatedImpact}/10`} color="secondary" />
                    </Box>

                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" color="text.secondary">
                        Expected results: {rec.timeToSee}
                      </Typography>
                      <LinearProgress 
                        variant="determinate" 
                        value={rec.estimatedImpact * 10} 
                        sx={{ mt: 1 }}
                      />
                    </Box>

                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" color="text.secondary">
                        {rec.resources.length} resources available
                      </Typography>
                      <Button
                        variant="contained"
                        size="small"
                        onClick={() => onApplyRecommendation?.(rec.id)}
                      >
                        Start Program
                      </Button>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Progress Tracking Preview */}
      <Accordion 
        expanded={expandedSections.includes('progress')}
        onChange={() => handleSectionToggle('progress')}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Timeline color="primary" />
            <Typography variant="h6">Progress Tracking</Typography>
            <Chip size="small" label="Coming Soon" color="info" />
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Alert severity="info" sx={{ mb: 2 }}>
            Advanced progress tracking features will be available soon, including:
          </Alert>
          <List>
            <ListItem>
              <ListItemIcon><CheckCircle color="success" /></ListItemIcon>
              <ListItemText primary="Detailed movement pattern analysis" />
            </ListItem>
            <ListItem>
              <ListItemIcon><CheckCircle color="success" /></ListItemIcon>
              <ListItemText primary="Biomechanical efficiency scoring" />
            </ListItem>
            <ListItem>
              <ListItemIcon><CheckCircle color="success" /></ListItemIcon>
              <ListItemText primary="Injury risk assessment" />
            </ListItem>
            <ListItem>
              <ListItemIcon><CheckCircle color="success" /></ListItemIcon>
              <ListItemText primary="Performance prediction modeling" />
            </ListItem>
          </List>
        </AccordionDetails>
      </Accordion>
    </Box>
  );
};

export default AdvancedFeedbackPreview;