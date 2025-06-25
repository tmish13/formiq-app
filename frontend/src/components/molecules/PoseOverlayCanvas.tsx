import React, { useRef, useEffect, useCallback, useState } from 'react';
import { Box, IconButton, Tooltip, useTheme } from '@mui/material';
import { 
  Visibility, 
  VisibilityOff, 
  Settings,
  GridOn,
  GridOff
} from '@mui/icons-material';
import { PoseOverlayProps, Keypoint, PoseIssue, OverlayConfig } from '../../types/ml';

/**
 * Canvas component for rendering pose keypoints and skeleton overlays
 * Supports user pose, reference pose, and issue highlighting
 */
export const PoseOverlayCanvas: React.FC<PoseOverlayProps> = ({
  userPose,
  referencePose,
  config = {},
  highlightIssues = [],
  onKeypointHover,
  onIssueClick
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [showOverlay, setShowOverlay] = useState(true);
  const [showGrid, setShowGrid] = useState(false);
  const theme = useTheme();

  // Default configuration
  const defaultConfig: OverlayConfig = {
    showSkeleton: true,
    showKeypoints: true,
    showConfidenceThreshold: 0.3,
    keypointRadius: 4,
    lineWidth: 2,
    colors: {
      keypoints: theme.palette.primary.main,
      skeleton: theme.palette.primary.main,
      reference: theme.palette.success.main,
      issues: theme.palette.error.main
    },
    ...config
  };

  // MediaPipe pose connections for skeleton rendering
  const POSE_CONNECTIONS = [
    // Torso
    ['left_shoulder', 'right_shoulder'],
    ['left_shoulder', 'left_hip'],
    ['right_shoulder', 'right_hip'],
    ['left_hip', 'right_hip'],
    
    // Left arm
    ['left_shoulder', 'left_elbow'],
    ['left_elbow', 'left_wrist'],
    ['left_wrist', 'left_pinky'],
    ['left_wrist', 'left_index'],
    ['left_wrist', 'left_thumb'],
    
    // Right arm
    ['right_shoulder', 'right_elbow'],
    ['right_elbow', 'right_wrist'],
    ['right_wrist', 'right_pinky'],
    ['right_wrist', 'right_index'],
    ['right_wrist', 'right_thumb'],
    
    // Left leg
    ['left_hip', 'left_knee'],
    ['left_knee', 'left_ankle'],
    ['left_ankle', 'left_heel'],
    ['left_ankle', 'left_foot_index'],
    
    // Right leg
    ['right_hip', 'right_knee'],
    ['right_knee', 'right_ankle'],
    ['right_ankle', 'right_heel'],
    ['right_ankle', 'right_foot_index'],
    
    // Face (simplified)
    ['nose', 'left_eye'],
    ['nose', 'right_eye'],
    ['left_eye', 'left_ear'],
    ['right_eye', 'right_ear']
  ];

  // Helper function to get keypoint by name
  const getKeypointByName = (keypoints: Keypoint[], name: string): Keypoint | undefined => {
    return keypoints.find(kp => kp.name === name);
  };

  // Helper function to check if keypoint meets confidence threshold
  const isKeypointVisible = (keypoint: Keypoint): boolean => {
    return keypoint.score >= (defaultConfig.showConfidenceThreshold || 0.3) && 
           keypoint.visible !== false;
  };

  // Draw grid for reference
  const drawGrid = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
    if (!showGrid) return;
    
    ctx.strokeStyle = theme.palette.grey[300];
    ctx.lineWidth = 1;
    ctx.setLineDash([5, 5]);
    
    // Vertical lines
    for (let x = 0; x <= width; x += 50) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    
    // Horizontal lines
    for (let y = 0; y <= height; y += 50) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
    
    ctx.setLineDash([]);
  };

  // Draw individual keypoint
  const drawKeypoint = (
    ctx: CanvasRenderingContext2D, 
    keypoint: Keypoint, 
    color: string,
    radius: number = defaultConfig.keypointRadius || 4
  ) => {
    if (!isKeypointVisible(keypoint)) return;
    
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(keypoint.x, keypoint.y, radius, 0, 2 * Math.PI);
    ctx.fill();
    
    // Add confidence indicator (opacity)
    ctx.fillStyle = `${color}${Math.round(keypoint.score * 255).toString(16).padStart(2, '0')}`;
    ctx.beginPath();
    ctx.arc(keypoint.x, keypoint.y, radius * 0.7, 0, 2 * Math.PI);
    ctx.fill();
  };

  // Draw skeleton connections
  const drawSkeleton = (
    ctx: CanvasRenderingContext2D, 
    keypoints: Keypoint[], 
    color: string,
    lineWidth: number = defaultConfig.lineWidth || 2
  ) => {
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    
    POSE_CONNECTIONS.forEach(([startName, endName]) => {
      const startPoint = getKeypointByName(keypoints, startName);
      const endPoint = getKeypointByName(keypoints, endName);
      
      if (startPoint && endPoint && 
          isKeypointVisible(startPoint) && 
          isKeypointVisible(endPoint)) {
        ctx.beginPath();
        ctx.moveTo(startPoint.x, startPoint.y);
        ctx.lineTo(endPoint.x, endPoint.y);
        ctx.stroke();
      }
    });
  };

  // Highlight pose issues
  const drawIssues = (ctx: CanvasRenderingContext2D, issues: PoseIssue[]) => {
    issues.forEach(issue => {
      issue.affected_keypoints.forEach(keypointName => {
        const keypoint = userPose ? getKeypointByName(userPose.keypoints, keypointName) : null;
        if (keypoint && isKeypointVisible(keypoint)) {
          // Draw issue highlight circle
          const issueColor = defaultConfig.colors?.issues || theme.palette.error.main;
          ctx.strokeStyle = issueColor;
          ctx.lineWidth = 3;
          ctx.setLineDash([5, 5]);
          ctx.beginPath();
          ctx.arc(keypoint.x, keypoint.y, 15, 0, 2 * Math.PI);
          ctx.stroke();
          ctx.setLineDash([]);
          
          // Draw severity indicator
          const severityColors = {
            low: theme.palette.warning.light,
            medium: theme.palette.warning.main,
            high: theme.palette.error.main
          };
          
          ctx.fillStyle = severityColors[issue.severity];
          ctx.font = '12px Arial';
          ctx.fillText('!', keypoint.x - 3, keypoint.y + 4);
        }
      });
    });
  };

  // Main drawing function
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    if (!showOverlay) return;
    
    // Draw grid
    drawGrid(ctx, canvas.width, canvas.height);
    
    // Draw reference pose first (background)
    if (referencePose && defaultConfig.showSkeleton) {
      drawSkeleton(
        ctx, 
        referencePose.keypoints, 
        defaultConfig.colors?.reference || theme.palette.success.main,
        (defaultConfig.lineWidth || 2) * 0.8
      );
    }
    
    if (referencePose && defaultConfig.showKeypoints) {
      referencePose.keypoints.forEach(keypoint => {
        drawKeypoint(
          ctx, 
          keypoint, 
          defaultConfig.colors?.reference || theme.palette.success.main,
          (defaultConfig.keypointRadius || 4) * 0.8
        );
      });
    }
    
    // Draw user pose (foreground)
    if (userPose && defaultConfig.showSkeleton) {
      drawSkeleton(
        ctx, 
        userPose.keypoints, 
        defaultConfig.colors?.skeleton || theme.palette.primary.main
      );
    }
    
    if (userPose && defaultConfig.showKeypoints) {
      userPose.keypoints.forEach(keypoint => {
        drawKeypoint(
          ctx, 
          keypoint, 
          defaultConfig.colors?.keypoints || theme.palette.primary.main
        );
      });
    }
    
    // Draw issues
    if (highlightIssues.length > 0) {
      drawIssues(ctx, highlightIssues);
    }
  }, [userPose, referencePose, defaultConfig, highlightIssues, showOverlay, showGrid, theme]);

  // Handle canvas resize
  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const container = canvas.parentElement;
    if (!container) return;
    
    const rect = container.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    
    draw();
  }, [draw]);

  // Handle mouse events for interactivity
  const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || !userPose) return;
    
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    // Check if click is near any issue
    const clickedIssue = highlightIssues.find(issue => {
      return issue.affected_keypoints.some(keypointName => {
        const keypoint = getKeypointByName(userPose.keypoints, keypointName);
        if (!keypoint || !isKeypointVisible(keypoint)) return false;
        
        const distance = Math.sqrt(
          Math.pow(x - keypoint.x, 2) + Math.pow(y - keypoint.y, 2)
        );
        return distance <= 20; // 20px click tolerance
      });
    });
    
    if (clickedIssue && onIssueClick) {
      onIssueClick(clickedIssue);
    }
  };

  const handleCanvasMouseMove = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || !userPose || !onKeypointHover) return;
    
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    // Find keypoint near cursor
    const hoveredKeypoint = userPose.keypoints.find(keypoint => {
      if (!isKeypointVisible(keypoint)) return false;
      
      const distance = Math.sqrt(
        Math.pow(x - keypoint.x, 2) + Math.pow(y - keypoint.y, 2)
      );
      return distance <= 10; // 10px hover tolerance
    });
    
    if (hoveredKeypoint) {
      onKeypointHover(hoveredKeypoint);
      canvas.style.cursor = 'pointer';
    } else {
      canvas.style.cursor = 'default';
    }
  };

  // Effects
  useEffect(() => {
    draw();
  }, [draw]);

  useEffect(() => {
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    return () => window.removeEventListener('resize', resizeCanvas);
  }, [resizeCanvas]);

  return (
    <Box position="relative" width="100%" height="100%">
      {/* Controls */}
      <Box 
        position="absolute" 
        top={8} 
        right={8} 
        zIndex={1}
        display="flex"
        gap={1}
      >
        <Tooltip title={showOverlay ? "Hide overlay" : "Show overlay"}>
          <IconButton
            size="small"
            onClick={() => setShowOverlay(!showOverlay)}
            sx={{ 
              bgcolor: 'background.paper', 
              '&:hover': { bgcolor: 'background.default' }
            }}
          >
            {showOverlay ? <Visibility /> : <VisibilityOff />}
          </IconButton>
        </Tooltip>
        
        <Tooltip title={showGrid ? "Hide grid" : "Show grid"}>
          <IconButton
            size="small"
            onClick={() => setShowGrid(!showGrid)}
            sx={{ 
              bgcolor: 'background.paper', 
              '&:hover': { bgcolor: 'background.default' }
            }}
          >
            {showGrid ? <GridOff /> : <GridOn />}
          </IconButton>
        </Tooltip>
      </Box>

      {/* Canvas */}
      <canvas
        ref={canvasRef}
        onClick={handleCanvasClick}
        onMouseMove={handleCanvasMouseMove}
        style={{
          width: '100%',
          height: '100%',
          display: 'block',
          cursor: 'default'
        }}
      />

      {/* Legend */}
      {showOverlay && (userPose || referencePose) && (
        <Box 
          position="absolute" 
          bottom={8} 
          left={8} 
          bgcolor="background.paper"
          p={1}
          borderRadius={1}
          boxShadow={1}
          fontSize="0.75rem"
        >
          {userPose && (
            <Box display="flex" alignItems="center" gap={1} mb={0.5}>
              <Box 
                width={12} 
                height={12} 
                borderRadius="50%" 
                bgcolor={defaultConfig.colors?.keypoints || theme.palette.primary.main}
              />
              <span>Your pose</span>
            </Box>
          )}
          {referencePose && (
            <Box display="flex" alignItems="center" gap={1} mb={0.5}>
              <Box 
                width={12} 
                height={12} 
                borderRadius="50%" 
                bgcolor={defaultConfig.colors?.reference || theme.palette.success.main}
              />
              <span>Reference</span>
            </Box>
          )}
          {highlightIssues.length > 0 && (
            <Box display="flex" alignItems="center" gap={1}>
              <Box 
                width={12} 
                height={12} 
                borderRadius="50%" 
                bgcolor={defaultConfig.colors?.issues || theme.palette.error.main}
              />
              <span>Issues</span>
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
};

export default PoseOverlayCanvas;