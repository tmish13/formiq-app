import React, { useState, useRef, useEffect } from 'react';
import { Box, Typography, Paper, Grid, List, ListItem, ListItemText, Divider, Chip, IconButton, Tabs, Tab, LinearProgress } from '@mui/material';
import { styled } from '@mui/system';
import { useFormCheck } from '../../hooks/useFormCheck';
import LoadingSpinner from '../../components/atoms/LoadingSpinner';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import InfoIcon from '@mui/icons-material/Info';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';

// Define styled components for better UI
const VideoContainer = styled(Box)(({ theme }) => ({
  position: 'relative',
  width: '100%',
  borderRadius: theme.shape.borderRadius,
  overflow: 'hidden',
  backgroundColor: '#000',
}));

const TimelineContainer = styled(Box)(({ theme }) => ({
  position: 'relative',
  width: '100%',
  height: '40px',
  marginTop: theme.spacing(1),
  backgroundColor: theme.palette.grey[200],
  borderRadius: theme.shape.borderRadius,
  overflow: 'hidden',
}));

const TimeMarker = styled(Box, {
  shouldForwardProp: (prop) => prop !== 'active' && prop !== 'markerColor'
})<{ left: string; active: boolean; markerColor: string }>(({ theme, left, active, markerColor }) => ({
  position: 'absolute',
  top: 0,
  left,
  width: '4px',
  height: '100%',
  backgroundColor: markerColor,
  cursor: 'pointer',
  zIndex: 10,
  opacity: active ? 1 : 0.7,
  transition: 'opacity 0.2s ease, transform 0.2s ease',
  '&:hover': {
    opacity: 1,
    transform: 'scaleX(1.5)',
  },
}));

const JointAngleCard = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
}));

const AngleVisualizer = styled(Box)(({ theme }) => ({
  position: 'relative',
  width: '100%',
  height: '30px',
  backgroundColor: theme.palette.grey[200],
  borderRadius: theme.shape.borderRadius,
  marginTop: theme.spacing(1),
}));

const AngleIndicator = styled(Box, {
  shouldForwardProp: (prop) => prop !== 'percent' && prop !== 'color'
})<{ percent: number; color: string }>(({ percent, color }) => ({
  position: 'absolute',
  top: 0,
  left: 0,
  width: `${percent}%`,
  height: '100%',
  backgroundColor: color,
  borderRadius: 'inherit',
}));

const SeverityIcon = ({ severity }: { severity: string }) => {
  switch (severity.toLowerCase()) {
    case 'low':
      return <InfoIcon fontSize="small" color="info" />;
    case 'medium':
      return <WarningIcon fontSize="small" color="warning" />;
    case 'high':
      return <ErrorIcon fontSize="small" color="error" />;
    default:
      return <InfoIcon fontSize="small" color="info" />;
  }
};

const Results: React.FC = () => {
  const { currentFormCheck, isLoading, error } = useFormCheck();
  const [activeTab, setActiveTab] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeFeedback, setActiveFeedback] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  // Handle video time updates
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
    };

    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('play', () => setIsPlaying(true));
    video.addEventListener('pause', () => setIsPlaying(false));

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('play', () => setIsPlaying(true));
      video.removeEventListener('pause', () => setIsPlaying(false));
    };
  }, []);

  // Seek to specific timestamp when clicking on timeline markers
  const seekToTime = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      if (!isPlaying) {
        videoRef.current.play();
      }
    }
  };

  // Toggle play/pause
  const togglePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  // Get severity color
  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'low':
        return '#2196F3'; // blue
      case 'medium':
        return '#FF9800'; // orange
      case 'high':
        return '#F44336'; // red
      default:
        return '#2196F3';
    }
  };

  // Calculate score color based on value
  const getScoreColor = (score: number) => {
    if (score >= 80) return '#4CAF50'; // green
    if (score >= 60) return '#FF9800'; // orange
    return '#F44336'; // red
  };

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography color="error">{error}</Typography>
      </Box>
    );
  }

  if (!currentFormCheck) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>No form check selected</Typography>
      </Box>
    );
  }

  // Sort feedback items by timestamp
  const sortedFeedbackItems = currentFormCheck.feedback_items 
    ? [...currentFormCheck.feedback_items].sort((a, b) => a.timestamp - b.timestamp)
    : [];

  // Calculate video duration (fallback to 60 seconds if not available)
  const videoDuration = currentFormCheck.form_metadata?.duration || 60;

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Form Analysis Results
      </Typography>
      
      <Grid container spacing={3}>
        {/* Video player section */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <VideoContainer>
              <video 
                ref={videoRef}
                src={currentFormCheck.video_url}
                controls
                width="100%"
                aria-label="Exercise video playback"
              />
              
              <Box sx={{ 
                position: 'absolute', 
                bottom: 0, 
                left: 0, 
                right: 0,
                p: 1,
                backgroundColor: 'rgba(0,0,0,0.5)',
                display: 'flex',
                alignItems: 'center'
              }}>
                <IconButton onClick={togglePlayPause} color="primary">
                  {isPlaying ? <PauseIcon /> : <PlayArrowIcon />}
                </IconButton>
                <LinearProgress 
                  variant="determinate" 
                  value={(currentTime / videoDuration) * 100}
                  sx={{ flexGrow: 1, mx: 1 }}
                />
                <Typography variant="caption" color="white">
                  {Math.floor(currentTime / 60)}:{Math.floor(currentTime % 60).toString().padStart(2, '0')}
                </Typography>
              </Box>
            </VideoContainer>
            
            {/* Timeline with feedback markers */}
            <TimelineContainer>
              {sortedFeedbackItems.map((item) => (
                <TimeMarker
                  key={item.id || 'unknown'}
                  left={`${(item.timestamp / videoDuration) * 100}%`}
                  active={activeFeedback === (item.id?.toString() || 'unknown')}
                  markerColor={getSeverityColor(item.severity)}
                  onClick={() => {
                    seekToTime(item.timestamp);
                    setActiveFeedback(item.id?.toString() || 'unknown');
                  }}
                  aria-label={`Jump to feedback at ${Math.floor(item.timestamp / 60)}:${Math.floor(item.timestamp % 60).toString().padStart(2, '0')}`}
                  role="button"
                  tabIndex={0}
                  aria-pressed={activeFeedback === (item.id?.toString() || 'unknown')}
                />
              ))}
            </TimelineContainer>
            
            {/* Exercise type and score */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
              <Chip 
                label={currentFormCheck.exercise_type?.replace('_', ' ')} 
                color="primary" 
                sx={{ textTransform: 'capitalize' }} 
              />
              <Chip 
                label={`Score: ${currentFormCheck.score || 'N/A'}`} 
                sx={{ 
                  backgroundColor: getScoreColor(currentFormCheck.score || 0),
                  color: 'white',
                  fontWeight: 'bold'
                }} 
              />
            </Box>
          </Paper>
        </Grid>
        
        {/* Score and info cards */}
        <Grid item xs={12} md={4}>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h5" gutterBottom>
                  Overall Assessment
                </Typography>
                <Typography paragraph>
                  {currentFormCheck.overall_feedback || 'No feedback available'}
                </Typography>
              </Paper>
            </Grid>
            
            {/* Show joint angles if available */}
            {currentFormCheck.form_metadata?.joint_angles && (
              <Grid item xs={12}>
                <JointAngleCard>
                  <Typography variant="h6" gutterBottom>
                    Joint Angles
                  </Typography>
                  <Grid container spacing={1}>
                    {Object.entries(currentFormCheck.form_metadata.joint_angles).map(([joint, angle]) => (
                      <Grid item xs={6} key={joint}>
                        <Typography variant="body2" component="div">
                          {joint.replace('_', ' ')}
                          <Typography variant="body1" fontWeight="bold">
                            {typeof angle === 'number' ? `${angle.toFixed(1)}°` : 'N/A'}
                          </Typography>
                          {typeof angle === 'number' && (
                            <AngleVisualizer>
                              <AngleIndicator 
                                percent={Math.min(angle / 180 * 100, 100)} 
                                color={angle > 150 || angle < 30 ? '#F44336' : angle > 120 || angle < 60 ? '#FF9800' : '#4CAF50'} 
                              />
                            </AngleVisualizer>
                          )}
                        </Typography>
                      </Grid>
                    ))}
                  </Grid>
                </JointAngleCard>
              </Grid>
            )}
          </Grid>
        </Grid>
        
        {/* Tabs for different feedback views */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Tabs value={activeTab} onChange={handleTabChange} centered sx={{ mb: 2 }}>
              <Tab label="All Feedback" />
              <Tab label="By Timestamp" />
              <Tab label="By Severity" />
            </Tabs>
            
            {/* All feedback tab */}
            {activeTab === 0 && (
              sortedFeedbackItems.length > 0 ? (
                <List>
                  {sortedFeedbackItems.map((item, index) => (
                    <React.Fragment key={item.id}>
                      <ListItem 
                        sx={{ 
                          borderLeft: `4px solid ${getSeverityColor(item.severity)}`,
                          bgcolor: activeFeedback === (item.id?.toString() || 'unknown') ? 'action.selected' : 'transparent'
                        }}
                        onClick={() => {
                          seekToTime(item.timestamp);
                          setActiveFeedback(item.id?.toString() || 'unknown');
                        }}
                        button
                        role="button"
                        aria-label={`View feedback at ${Math.floor(item.timestamp / 60)}:${Math.floor(item.timestamp % 60).toString().padStart(2, '0')}`}
                      >
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <SeverityIcon severity={item.severity} />
                              <Typography variant="subtitle1">
                                {item.type?.charAt(0).toUpperCase() + item.type?.slice(1).replace('_', ' ')} 
                                <Typography component="span" variant="caption" sx={{ ml: 1 }}>
                                  (at {Math.floor(item.timestamp / 60)}:{Math.floor(item.timestamp % 60).toString().padStart(2, '0')})
                                </Typography>
                              </Typography>
                            </Box>
                          }
                          secondary={
                            <>
                              <Typography component="span" variant="body2">
                                {item.description || item.message}
                              </Typography>
                              {item.suggestions && (
                                <Typography component="div" variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                  <strong>Suggestions:</strong>
                                  <ul style={{ margin: '4px 0', paddingLeft: '20px' }}>
                                    {Array.isArray(item.suggestions) 
                                      ? item.suggestions.map((s, i) => <li key={i}>{s}</li>)
                                      : <li>{item.suggestions}</li>
                                    }
                                  </ul>
                                </Typography>
                              )}
                              {item.joint_angles && (
                                <Typography component="div" variant="body2" sx={{ mt: 1 }}>
                                  <strong>Joint Angles:</strong>
                                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 0.5 }}>
                                    {Object.entries(item.joint_angles).map(([joint, angle]) => (
                                      <Chip 
                                        key={joint} 
                                        size="small"
                                        label={`${joint.replace('_', ' ')}: ${typeof angle === 'number' ? `${angle.toFixed(1)}°` : angle}`} 
                                      />
                                    ))}
                                  </Box>
                                </Typography>
                              )}
                            </>
                          }
                        />
                      </ListItem>
                      {index < sortedFeedbackItems.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Typography align="center" color="text.secondary">
                  No feedback items available
                </Typography>
              )
            )}
            
            {/* Timestamp tab */}
            {activeTab === 1 && (
              sortedFeedbackItems.length > 0 ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {/* Group by rough timestamp (within 2 seconds) */}
                  {Object.entries(
                    sortedFeedbackItems.reduce((acc, item) => {
                      const timeKey = Math.floor(item.timestamp / 2) * 2;
                      if (!acc[timeKey]) acc[timeKey] = [];
                      acc[timeKey].push(item);
                      return acc;
                    }, {} as Record<number, typeof sortedFeedbackItems>)
                  )
                    .sort(([a], [b]) => Number(a) - Number(b))
                    .map(([time, items]) => (
                      <Paper key={time} sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>
                          At {Math.floor(Number(time) / 60)}:{Math.floor(Number(time) % 60).toString().padStart(2, '0')}
                          <IconButton 
                            size="small" 
                            onClick={() => seekToTime(Number(time))}
                            aria-label={`Play video at ${Math.floor(Number(time) / 60)}:${Math.floor(Number(time) % 60).toString().padStart(2, '0')}`}
                          >
                            <PlayArrowIcon fontSize="small" />
                          </IconButton>
                        </Typography>
                        <List>
                          {items.map((item, idx) => (
                            <React.Fragment key={item.id}>
                              <ListItem sx={{ py: 0.5 }}>
                                <SeverityIcon severity={item.severity} />
                                <ListItemText 
                                  sx={{ ml: 1 }}
                                  primary={item.type?.charAt(0).toUpperCase() + item.type?.slice(1).replace('_', ' ')}
                                  secondary={item.description || item.message}
                                />
                              </ListItem>
                              {idx < items.length - 1 && <Divider />}
                            </React.Fragment>
                          ))}
                        </List>
                      </Paper>
                    ))}
                </Box>
              ) : (
                <Typography align="center" color="text.secondary">
                  No feedback items available
                </Typography>
              )
            )}
            
            {/* Severity tab */}
            {activeTab === 2 && (
              sortedFeedbackItems.length > 0 ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {/* High severity issues */}
                  {(() => {
                    const highSeverity = sortedFeedbackItems.filter(item => 
                      item.severity.toLowerCase() === 'high');
                    
                    return highSeverity.length > 0 ? (
                      <Paper sx={{ p: 2, borderLeft: '4px solid #F44336' }}>
                        <Typography variant="h6" gutterBottom color="error">
                          Critical Issues
                        </Typography>
                        <List>
                          {highSeverity.map((item, idx) => (
                            <React.Fragment key={item.id}>
                              <ListItem 
                                onClick={() => seekToTime(item.timestamp)}
                                sx={{ cursor: 'pointer' }}
                              >
                                <ListItemText 
                                  primary={item.type?.charAt(0).toUpperCase() + item.type?.slice(1).replace('_', ' ')}
                                  secondary={
                                    <>
                                      <Typography variant="body2" component="span">
                                        {item.description || item.message}
                                      </Typography>
                                      <Typography variant="caption" component="div" sx={{ mt: 0.5 }}>
                                        At {Math.floor(item.timestamp / 60)}:{Math.floor(item.timestamp % 60).toString().padStart(2, '0')}
                                      </Typography>
                                    </>
                                  }
                                />
                              </ListItem>
                              {idx < highSeverity.length - 1 && <Divider />}
                            </React.Fragment>
                          ))}
                        </List>
                      </Paper>
                    ) : null;
                  })()}
                  
                  {/* Medium severity issues */}
                  {(() => {
                    const mediumSeverity = sortedFeedbackItems.filter(item => 
                      item.severity.toLowerCase() === 'medium');
                    
                    return mediumSeverity.length > 0 ? (
                      <Paper sx={{ p: 2, borderLeft: '4px solid #FF9800' }}>
                        <Typography variant="h6" gutterBottom color="warning.main">
                          Issues to Improve
                        </Typography>
                        <List>
                          {mediumSeverity.map((item, idx) => (
                            <React.Fragment key={item.id}>
                              <ListItem 
                                onClick={() => seekToTime(item.timestamp)}
                                sx={{ cursor: 'pointer' }}
                              >
                                <ListItemText 
                                  primary={item.type?.charAt(0).toUpperCase() + item.type?.slice(1).replace('_', ' ')}
                                  secondary={
                                    <>
                                      <Typography variant="body2" component="span">
                                        {item.description || item.message}
                                      </Typography>
                                      <Typography variant="caption" component="div" sx={{ mt: 0.5 }}>
                                        At {Math.floor(item.timestamp / 60)}:{Math.floor(item.timestamp % 60).toString().padStart(2, '0')}
                                      </Typography>
                                    </>
                                  }
                                />
                              </ListItem>
                              {idx < mediumSeverity.length - 1 && <Divider />}
                            </React.Fragment>
                          ))}
                        </List>
                      </Paper>
                    ) : null;
                  })()}
                  
                  {/* Low severity issues */}
                  {(() => {
                    const lowSeverity = sortedFeedbackItems.filter(item => 
                      item.severity.toLowerCase() === 'low');
                    
                    return lowSeverity.length > 0 ? (
                      <Paper sx={{ p: 2, borderLeft: '4px solid #2196F3' }}>
                        <Typography variant="h6" gutterBottom color="info.main">
                          Minor Adjustments
                        </Typography>
                        <List>
                          {lowSeverity.map((item, idx) => (
                            <React.Fragment key={item.id}>
                              <ListItem 
                                onClick={() => seekToTime(item.timestamp)}
                                sx={{ cursor: 'pointer' }}
                              >
                                <ListItemText 
                                  primary={item.type?.charAt(0).toUpperCase() + item.type?.slice(1).replace('_', ' ')}
                                  secondary={
                                    <>
                                      <Typography variant="body2" component="span">
                                        {item.description || item.message}
                                      </Typography>
                                      <Typography variant="caption" component="div" sx={{ mt: 0.5 }}>
                                        At {Math.floor(item.timestamp / 60)}:{Math.floor(item.timestamp % 60).toString().padStart(2, '0')}
                                      </Typography>
                                    </>
                                  }
                                />
                              </ListItem>
                              {idx < lowSeverity.length - 1 && <Divider />}
                            </React.Fragment>
                          ))}
                        </List>
                      </Paper>
                    ) : null;
                  })()}
                </Box>
              ) : (
                <Typography align="center" color="text.secondary">
                  No feedback items available
                </Typography>
              )
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Results; 