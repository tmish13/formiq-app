import React, { useRef, useEffect } from 'react';
import { Box, Typography } from '@mui/material';
import { Keypoint } from '@tensorflow-models/pose-detection';
import { JointAngle } from '../../types/formAnalysis';

interface PoseVisualizationProps {
  keypoints: Keypoint[];
  angles: JointAngle[];
}

export const PoseVisualization: React.FC<PoseVisualizationProps> = ({ keypoints, angles }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Set canvas dimensions
    canvas.width = 640;
    canvas.height = 480;
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw keypoints and connections
    drawPose(ctx, keypoints);
    
    // Draw angles
    drawAngles(ctx, keypoints, angles);
    
  }, [keypoints, angles]);
  
  const drawPose = (ctx: CanvasRenderingContext2D, keypoints: Keypoint[]) => {
    // Draw keypoints
    keypoints.forEach(keypoint => {
      if (keypoint.score && keypoint.score > 0.3) {
        ctx.beginPath();
        ctx.arc(keypoint.x, keypoint.y, 5, 0, 2 * Math.PI);
        ctx.fillStyle = 'rgba(0, 255, 0, 0.8)';
        ctx.fill();
        ctx.strokeStyle = 'white';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    });
    
    // Draw connections between keypoints
    const connections = [
      // Torso
      ['left_shoulder', 'right_shoulder'],
      ['left_shoulder', 'left_hip'],
      ['right_shoulder', 'right_hip'],
      ['left_hip', 'right_hip'],
      
      // Left arm
      ['left_shoulder', 'left_elbow'],
      ['left_elbow', 'left_wrist'],
      
      // Right arm
      ['right_shoulder', 'right_elbow'],
      ['right_elbow', 'right_wrist'],
      
      // Left leg
      ['left_hip', 'left_knee'],
      ['left_knee', 'left_ankle'],
      
      // Right leg
      ['right_hip', 'right_knee'],
      ['right_knee', 'right_ankle']
    ];
    
    connections.forEach(([start, end]) => {
      const startPoint = keypoints.find(kp => kp.name === start);
      const endPoint = keypoints.find(kp => kp.name === end);
      
      if (startPoint && endPoint && startPoint.score && endPoint.score && 
          startPoint.score > 0.3 && endPoint.score > 0.3) {
        ctx.beginPath();
        ctx.moveTo(startPoint.x, startPoint.y);
        ctx.lineTo(endPoint.x, endPoint.y);
        ctx.strokeStyle = 'rgba(0, 255, 0, 0.8)';
        ctx.lineWidth = 3;
        ctx.stroke();
      }
    });
  };
  
  const drawAngles = (ctx: CanvasRenderingContext2D, keypoints: Keypoint[], angles: JointAngle[]) => {
    angles.forEach(angle => {
      const jointName = angle.joint;
      const angleValue = angle.angle;
      
      // Find the keypoints for this joint
      let p1, p2, p3;
      
      if (jointName === 'left_elbow') {
        p1 = keypoints.find(kp => kp.name === 'left_shoulder');
        p2 = keypoints.find(kp => kp.name === 'left_elbow');
        p3 = keypoints.find(kp => kp.name === 'left_wrist');
      } else if (jointName === 'right_elbow') {
        p1 = keypoints.find(kp => kp.name === 'right_shoulder');
        p2 = keypoints.find(kp => kp.name === 'right_elbow');
        p3 = keypoints.find(kp => kp.name === 'right_wrist');
      } else if (jointName === 'left_knee') {
        p1 = keypoints.find(kp => kp.name === 'left_hip');
        p2 = keypoints.find(kp => kp.name === 'left_knee');
        p3 = keypoints.find(kp => kp.name === 'left_ankle');
      } else if (jointName === 'right_knee') {
        p1 = keypoints.find(kp => kp.name === 'right_hip');
        p2 = keypoints.find(kp => kp.name === 'right_knee');
        p3 = keypoints.find(kp => kp.name === 'right_ankle');
      }
      
      if (p1 && p2 && p3 && p1.score && p2.score && p3.score && 
          p1.score > 0.3 && p2.score > 0.3 && p3.score > 0.3) {
        // Draw angle arc
        ctx.beginPath();
        ctx.arc(p2.x, p2.y, 20, 0, 2 * Math.PI);
        ctx.strokeStyle = 'rgba(255, 255, 0, 0.5)';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // Draw angle value
        ctx.font = '14px Arial';
        ctx.fillStyle = 'white';
        ctx.textAlign = 'center';
        ctx.fillText(`${Math.round(angleValue)}°`, p2.x, p2.y - 25);
      }
    });
  };
  
  return (
    <Box sx={{ position: 'relative', width: '100%', height: 360 }}>
      <canvas 
        ref={canvasRef} 
        style={{ 
          width: '100%', 
          height: '100%', 
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          borderRadius: '4px'
        }} 
      />
      <Box sx={{ mt: 1 }}>
        <Typography variant="body2" color="text.secondary">
          Green: Detected pose | Yellow: Joint angles
        </Typography>
      </Box>
    </Box>
  );
}; 