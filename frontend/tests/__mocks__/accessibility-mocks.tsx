import React from 'react';

// Mock for WorkoutTracking component
export const MockWorkoutTracking: React.FC = () => {
  return (
    <div data-testid="workout-tracking">
      <h4>Workout Tracking</h4>
      <div>
        <button aria-label="Start Workout">Start Workout</button>
        <button aria-label="End Workout">End Workout</button>
      </div>
    </div>
  );
};

// Mock for CameraCapture component
export interface FormTip {
  id: string;
  message: string;
  timingMs: number;
}

export interface MockCameraCaptureProps {
  onVideoCapture: (file: File) => void;
  maxDuration: number;
  formTips: FormTip[];
  formScore?: number;
}

export const MockCameraCapture: React.FC<MockCameraCaptureProps> = ({
  onVideoCapture,
  formTips,
  formScore
}) => {
  return (
    <div data-testid="camera-capture">
      <button aria-label="Start Recording">Start Recording</button>
      <div>
        {formTips.map(tip => (
          <div key={tip.id} data-type="warning">{tip.message}</div>
        ))}
        {formScore && <span data-score={formScore}>{formScore}</span>}
      </div>
      <input type="file" accept="video/*" aria-label="Choose video file" />
    </div>
  );
};

// Mock for FormAnalysis component
export const MockFormAnalysis: React.FC = () => {
  return (
    <div data-testid="form-analysis">
      <h4>Form Analysis</h4>
      <form>
        <button type="submit" aria-label="Submit Form">Submit</button>
      </form>
    </div>
  );
}; 