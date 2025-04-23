import React, { useEffect, useRef, useState } from 'react';
import { useSelector } from 'react-redux';

interface RootState {
  auth: {
    isAuthenticated: boolean;
  };
}

const CameraCapture: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState<string>('');
  const isAuthenticated = useSelector((state: RootState) => state.auth.isAuthenticated);

  useEffect(() => {
    if (!isAuthenticated) return;

    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (err) {
        setError('Failed to access camera');
      }
    };

    startCamera();

    return () => {
      const stream = videoRef.current?.srcObject as MediaStream;
      stream?.getTracks().forEach(track => track.stop());
    };
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return <div>Please log in to access the camera</div>;
  }

  if (error) {
    return <div>{error}</div>;
  }

  return (
    <div>
      <video ref={videoRef} autoPlay playsInline />
    </div>
  );
};

export default CameraCapture; 