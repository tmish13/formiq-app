import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Slider,
  IconButton,
  Tooltip,
  Grid,
  Switch,
  FormControlLabel,
  Chip,
  Button,
  useTheme
} from '@mui/material';
import {
  PlayArrow,
  Pause,
  SkipPrevious,
  SkipNext,
  CompareArrows,
  Download,
  Fullscreen,
  Timeline
} from '@mui/icons-material';
import { PoseOverlayCanvas } from './PoseOverlayCanvas';
import { PoseData, PoseIssue, OverlayConfig } from '../../types/ml';
import { ExerciseType } from '../../types/formCheck';

interface PoseComparisonViewProps {
  formCheckId: string;
  exerciseType: ExerciseType;
  userPoseData?: PoseData[];
  referencePoseData?: PoseData[];
  detectedIssues?: PoseIssue[];
  videoElement?: HTMLVideoElement;
  showTimeline?: boolean;
  allowScrubbing?: boolean;
  onExportFrame?: (frameIndex: number) => void;
  onFullscreen?: () => void;
}

/**
 * Component for side-by-side pose comparison with timeline controls
 * Allows frame-by-frame analysis and issue highlighting
 */
export const PoseComparisonView: React.FC<PoseComparisonViewProps> = ({
  formCheckId,
  exerciseType,
  userPoseData = [],
  referencePoseData = [],
  detectedIssues = [],
  videoElement,
  showTimeline = true,
  allowScrubbing = true,
  onExportFrame,
  onFullscreen
}) => {
  const theme = useTheme();
  const [currentFrame, setCurrentFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showReference, setShowReference] = useState(true);
  const [showIssues, setShowIssues] = useState(true);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [selectedIssue, setSelectedIssue] = useState<PoseIssue | null>(null);
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const maxFrames = Math.max(userPoseData.length, referencePoseData.length);
  
  // Current pose data for display
  const currentUserPose = userPoseData[currentFrame];
  const currentReferencePose = referencePoseData[currentFrame];
  
  // Issues for current frame
  const currentFrameIssues = showIssues ? detectedIssues.filter(issue => {
    const frameTime = currentFrame * (1000 / 30); // Assuming 30fps
    return issue.timestamp ? Math.abs(issue.timestamp - frameTime) < 100 : true;
  }) : [];

  // Overlay configuration
  const overlayConfig: OverlayConfig = {
    showSkeleton: true,
    showKeypoints: true,
    showConfidenceThreshold: 0.3,
    keypointRadius: 5,
    lineWidth: 2,
    colors: {
      keypoints: theme.palette.primary.main,
      skeleton: theme.palette.primary.main,
      reference: theme.palette.success.main,
      issues: theme.palette.error.main
    }
  };

  // Timeline controls
  const handlePlayPause = () => {
    setIsPlaying(!isPlaying);
  };

  const handleFrameChange = (newFrame: number) => {
    setCurrentFrame(Math.max(0, Math.min(newFrame, maxFrames - 1)));
    if (videoElement) {
      videoElement.currentTime = newFrame / 30; // Assuming 30fps
    }
  };

  const handlePreviousFrame = () => {
    handleFrameChange(currentFrame - 1);
  };

  const handleNextFrame = () => {
    handleFrameChange(currentFrame + 1);
  };

  const handleSliderChange = (_: Event, value: number | number[]) => {
    const frameIndex = value as number;
    handleFrameChange(frameIndex);
  };

  const handleKeypointHover = (keypoint: any) => {
    // Could show tooltip with keypoint info
    console.log('Hovered keypoint:', keypoint);
  };

  const handleIssueClick = (issue: PoseIssue) => {
    setSelectedIssue(issue);
  };

  const handleExportFrame = () => {
    if (onExportFrame) {
      onExportFrame(currentFrame);
    }
  };

  // Auto-play functionality
  useEffect(() => {
    if (isPlaying && maxFrames > 0) {
      intervalRef.current = setInterval(() => {
        setCurrentFrame(prev => {
          const next = prev + 1;
          if (next >= maxFrames) {
            setIsPlaying(false);
            return 0; // Loop back to start
          }
          return next;
        });
      }, 1000 / (30 * playbackSpeed)); // Adjust for playback speed
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isPlaying, maxFrames, playbackSpeed]);

  // Format time display
  const formatTime = (frame: number): string => {
    const seconds = frame / 30; // Assuming 30fps
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    const milliseconds = Math.floor((seconds % 1) * 1000);
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}.${milliseconds.toString().padStart(3, '0')}`;
  };

  if (maxFrames === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Pose Comparison
          </Typography>
          <Typography color="text.secondary">
            No pose data available for comparison.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        {/* Header */}
        <Box display="flex" alignItems="center" justifyContent="between" mb={2}>
          <Typography variant="h6" fontWeight="bold">
            Pose Analysis - {exerciseType}
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            <Chip 
              label={`Frame ${currentFrame + 1}/${maxFrames}`}
              size="small"
              color="primary"
              variant="outlined"
            />
            <Chip 
              label={formatTime(currentFrame)}
              size="small"
              variant="outlined"
            />
          </Box>
        </Box>

        {/* Controls */}
        <Box display="flex" alignItems="center" gap={2} mb={2}>
          <FormControlLabel
            control={
              <Switch
                checked={showReference}
                onChange={(e) => setShowReference(e.target.checked)}
                size="small"
              />
            }
            label="Reference Pose"
          />
          <FormControlLabel
            control={
              <Switch
                checked={showIssues}
                onChange={(e) => setShowIssues(e.target.checked)}
                size="small"
              />
            }
            label="Show Issues"
          />
          
          {onExportFrame && (
            <Tooltip title="Export current frame">
              <IconButton onClick={handleExportFrame} size="small">
                <Download />
              </IconButton>
            </Tooltip>
          )}
          
          {onFullscreen && (
            <Tooltip title="Fullscreen">
              <IconButton onClick={onFullscreen} size="small">
                <Fullscreen />
              </IconButton>
            </Tooltip>
          )}
        </Box>

        {/* Main comparison view */}
        <Grid container spacing={2}>
          <Grid item xs={12} md={8}>
            <Box 
              position="relative" 
              height={400} 
              bgcolor="grey.100" 
              borderRadius={1}
              overflow="hidden"
            >
              <PoseOverlayCanvas
                userPose={currentUserPose}
                referencePose={showReference ? currentReferencePose : undefined}
                config={overlayConfig}
                highlightIssues={currentFrameIssues}
                onKeypointHover={handleKeypointHover}
                onIssueClick={handleIssueClick}
              />
            </Box>
          </Grid>
          
          <Grid item xs={12} md={4}>
            {/* Issue details */}
            {selectedIssue ? (
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Issue Details
                  </Typography>
                  <Chip 
                    label={selectedIssue.severity.toUpperCase()}
                    color={selectedIssue.severity === 'high' ? 'error' : selectedIssue.severity === 'medium' ? 'warning' : 'info'}
                    size="small"
                    sx={{ mb: 1 }}
                  />
                  <Typography variant="body2" gutterBottom>
                    <strong>Type:</strong> {selectedIssue.type}
                  </Typography>
                  <Typography variant="body2" gutterBottom>
                    <strong>Description:</strong> {selectedIssue.description}
                  </Typography>
                  {selectedIssue.suggestions.length > 0 && (
                    <>
                      <Typography variant="body2" fontWeight={500} mt={2} mb={1}>
                        Suggestions:
                      </Typography>
                      <ul style={{ margin: 0, paddingLeft: '1.2rem' }}>
                        {selectedIssue.suggestions.map((suggestion, index) => (
                          <li key={index}>
                            <Typography variant="body2">{suggestion}</Typography>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                  <Button 
                    size="small" 
                    onClick={() => setSelectedIssue(null)}
                    sx={{ mt: 2 }}
                  >
                    Close
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Frame Analysis
                  </Typography>
                  {currentFrameIssues.length > 0 ? (
                    <>
                      <Typography variant="body2" color="error" gutterBottom>
                        {currentFrameIssues.length} issue(s) detected
                      </Typography>
                      {currentFrameIssues.map((issue, index) => (
                        <Chip
                          key={index}
                          label={issue.type}
                          size="small"
                          color="error"
                          variant="outlined"
                          onClick={() => handleIssueClick(issue)}
                          sx={{ mr: 1, mb: 1, cursor: 'pointer' }}
                        />
                      ))}
                    </>
                  ) : (
                    <Typography variant="body2" color="success.main">
                      No issues detected in this frame
                    </Typography>
                  )}
                </CardContent>
              </Card>
            )}
          </Grid>
        </Grid>

        {/* Timeline controls */}
        {showTimeline && (
          <Box mt={3}>
            {/* Playback controls */}
            <Box display="flex" alignItems="center" gap={2} mb={2}>
              <IconButton onClick={handlePreviousFrame} disabled={currentFrame === 0}>
                <SkipPrevious />
              </IconButton>
              <IconButton onClick={handlePlayPause}>
                {isPlaying ? <Pause /> : <PlayArrow />}
              </IconButton>
              <IconButton onClick={handleNextFrame} disabled={currentFrame >= maxFrames - 1}>
                <SkipNext />
              </IconButton>
              
              <Typography variant="body2" sx={{ minWidth: 80 }}>
                Speed: {playbackSpeed}x
              </Typography>
              <Slider
                value={playbackSpeed}
                onChange={(_, value) => setPlaybackSpeed(value as number)}
                min={0.25}
                max={2}
                step={0.25}
                sx={{ width: 100 }}
                size="small"
              />
            </Box>

            {/* Timeline slider */}
            {allowScrubbing && (
              <Box>
                <Slider
                  value={currentFrame}
                  onChange={handleSliderChange}
                  min={0}
                  max={maxFrames - 1}
                  step={1}
                  marks={detectedIssues.map(issue => ({
                    value: Math.round((issue.timestamp || 0) * 30 / 1000), // Convert timestamp to frame
                    label: ''
                  })).filter((mark, index, self) => 
                    self.findIndex(m => m.value === mark.value) === index
                  )}
                  sx={{
                    '& .MuiSlider-mark': {
                      backgroundColor: theme.palette.error.main,
                      height: 8,
                      width: 2
                    }
                  }}
                />
                <Box display="flex" justifyContent="between" mt={1}>
                  <Typography variant="caption" color="text.secondary">
                    {formatTime(0)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {formatTime(maxFrames - 1)}
                  </Typography>
                </Box>
              </Box>
            )}
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default PoseComparisonView;