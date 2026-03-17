import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Camera,
  Ruler,
  Sun,
  Shield,
  Square,
  RotateCcw,
  CheckCircle,
  ArrowLeft,
  Target,
  Timer,
  Video,
  Eye,
  X,
  Play,
  Upload,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { Badge } from '../components/ui/badge';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../hooks/use-toast';
import AppLayout from '../components/layout/AppLayout';

// Import our backend services
import { VideoUploadProgress } from '../services/videoService';
import { formCheckService } from '../services/formCheckService';
import { logEvent, logBetaEvent } from '../utils/logEvent';

/** Read video duration in seconds from a File using a temporary <video> element.
 *  Resolves within 5 seconds; rejects if metadata is unreadable or times out. */
function getVideoDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const video = document.createElement('video');
    video.preload = 'metadata';
    const cleanup = () => URL.revokeObjectURL(url);
    const timeoutId = setTimeout(() => { cleanup(); reject(new Error('Metadata timeout')); }, 5000);
    video.onloadedmetadata = () => { clearTimeout(timeoutId); cleanup(); resolve(video.duration); };
    video.onerror = () => { clearTimeout(timeoutId); cleanup(); reject(new Error('Cannot read video metadata')); };
    video.src = url;
  });
}

type RecordingState =
  | 'setup'
  | 'ready'
  | 'countdown'
  | 'recording'
  | 'preview'
  | 'uploading'
  | 'error'
  | 'processing'
  | 'complete';

type CameraErrorType = 'permission' | 'notfound' | 'generic' | null;

const MIN_RECORD_SECONDS = 2;
// 6-second auto-stop. setInterval drift means the blob may run ~6.05–6.15 s,
// which is fine — the backend gate is > 6.5 s (not > 6.0 s), giving a 0.5 s
// safety margin above the product max.
const MAX_RECORD_SECONDS = 6;

const EXERCISE_OPTIONS = [
  { value: 'squat', label: 'Squat', supported: true },
  { value: 'deadlift', label: 'Deadlift', supported: false },
  { value: 'bench_press', label: 'Bench Press', supported: false },
  { value: 'overhead_press', label: 'Overhead Press', supported: false },
  { value: 'barbell_row', label: 'Barbell Row', supported: false },
  { value: 'pullup', label: 'Pull-up', supported: false },
  { value: 'pushup', label: 'Push-up', supported: false },
] as const;

export default function RecordPage() {
  const [recordingState, setRecordingState] = useState<RecordingState>('setup');
  const [countdown, setCountdown] = useState(3);
  const [recordingTime, setRecordingTime] = useState(0);
  const [uploadProgress, setUploadProgress] = useState<VideoUploadProgress | null>(null);
  const [formCheckId, setFormCheckId] = useState<string | null>(null);
  const [formScore, setFormScore] = useState<number | null>(null);
  const [currentExercise, setCurrentExercise] = useState('squat');
  const [shadowMode, setShadowMode] = useState(false);
  const [displayedScore, setDisplayedScore] = useState(0);
  const [weightLb, setWeightLb] = useState<string>('');

  const [setupChecklist, setSetupChecklist] = useState({
    angle: false,
    distance: false,
    lighting: false,
    visibility: false,
    stability: false,
  });
  const [currentSetupStep, setCurrentSetupStep] = useState(0);
  const [cameraError, setCameraError] = useState(false);
  const [cameraErrorType, setCameraErrorType] = useState<CameraErrorType>(null);

  const [tooShortError, setTooShortError] = useState(false);

  // Camera control — front/back toggle
  const [facingMode, setFacingMode] = useState<'environment' | 'user'>('environment');
  const facingModeRef = useRef<'environment' | 'user'>('environment');
  // Readiness indicator: initializing → positioning → ready
  type ReadinessState = 'initializing' | 'positioning' | 'ready';
  const [readiness, setReadiness] = useState<ReadinessState>('initializing');
  const readinessFiredRef = useRef(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const recordingStartTimeRef = useRef<number | null>(null);
  const recordingBlobRef = useRef<Blob | null>(null);
  // Track preview URL for cleanup (state might be stale in effect)
  const previewUrlRef = useRef<string | null>(null);
  // Actual MIME type used by the MediaRecorder instance — may differ from 'video/webm'
  // on iOS Safari which records video/mp4. Read after creation, used for blob + file.
  const recordingMimeRef = useRef<string>('video/webm');
  // Upload timeout — 60s wall-clock limit; cleared on success or error
  const uploadTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const uploadSucceededRef = useRef(false);

  const navigate = useNavigate();
  const { toast } = useToast();

  const setupSteps: Array<{
    key: 'angle' | 'distance' | 'lighting' | 'visibility' | 'stability';
    label: string;
    description: string;
    icon: React.ComponentType<{ className?: string }>;
  }> = [
    {
      key: 'angle',
      label: 'Film from side or back angle',
      description: 'Side/back view is required — front angle cannot evaluate form',
      icon: Ruler,
    },
    {
      key: 'distance',
      label: 'Position camera 6 feet away',
      description: 'Full body should be visible',
      icon: Target,
    },
    {
      key: 'lighting',
      label: 'Ensure good lighting',
      description: 'Avoid shadows on your body',
      icon: Sun,
    },
    {
      key: 'visibility',
      label: 'Clear view of your form',
      description: 'No obstructions in the way',
      icon: Eye,
    },
    {
      key: 'stability',
      label: 'Phone is stable',
      description: 'Use a tripod or stable surface',
      icon: Shield,
    },
  ];

  // Cleanup: stop camera tracks and revoke preview URL on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
        previewUrlRef.current = null;
      }
    };
  }, []);

  // Keep facingModeRef in sync so initializeCamera() doesn't stale-close over state
  useEffect(() => { facingModeRef.current = facingMode; }, [facingMode]);

  // Attach camera stream to video element when entering recording-related states
  useEffect(() => {
    if (recordingState === 'ready') {
      if (streamRef.current) {
        if (videoRef.current && !videoRef.current.srcObject) {
          videoRef.current.srcObject = streamRef.current;
        }
        // Reset readiness each time user returns to ready state
        setReadiness('positioning');
        readinessFiredRef.current = false;
      } else {
        initializeCamera();
      }
    } else if (recordingState === 'countdown' || recordingState === 'recording') {
      // Re-attach stream to the full-screen overlay's video element
      if (streamRef.current && videoRef.current && !videoRef.current.srcObject) {
        videoRef.current.srcObject = streamRef.current;
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recordingState]);

  // Countdown tick — shows 3 → 2 → 1 → "Go!" → starts recording
  useEffect(() => {
    if (recordingState !== 'countdown') return;
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown((c) => c - 1), 1000);
      return () => clearTimeout(timer);
    }
    // countdown === 0: show "Go!" for 600 ms then start recording
    const timer = setTimeout(() => startRecording(), 600);
    return () => clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recordingState, countdown]);

  // Recording timer + auto-stop at MAX_RECORD_SECONDS
  useEffect(() => {
    if (recordingState !== 'recording') return;
    const interval = setInterval(() => {
      setRecordingTime((prev) => {
        const next = prev + 1;
        if (next >= MAX_RECORD_SECONDS) {
          clearInterval(interval);
          stopRecording();
        }
        return next;
      });
    }, 1000);
    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recordingState]);

  // Auto-transition positioning → ready after 3.5 s; fire sound + haptic on back camera
  useEffect(() => {
    if (readiness !== 'positioning') return;
    const t = setTimeout(() => {
      setReadiness('ready');
      if (facingModeRef.current === 'environment' && !readinessFiredRef.current) {
        readinessFiredRef.current = true;
        // Subtle beep — signals readiness when user can't see the screen (back camera)
        try {
          const AC = (window as any).AudioContext || (window as any).webkitAudioContext;
          if (AC) {
            const ctx: AudioContext = new AC();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.type = 'sine';
            osc.frequency.value = 880;
            gain.gain.setValueAtTime(0.12, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.3);
          }
        } catch { /* audio blocked or not available */ }
        // Haptic pulse
        try { if (navigator.vibrate) navigator.vibrate(150); } catch { /* not supported */ }
      }
    }, 3500);
    return () => clearTimeout(t);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [readiness]);

  const getCameraErrorMessage = (): string => {
    switch (cameraErrorType) {
      case 'permission':
        return 'Camera permission is blocked. Enable camera access in your browser settings and try again.';
      case 'notfound':
        return 'No camera found. Try connecting a camera or switching devices.';
      default:
        return 'Could not access camera. Please try again.';
    }
  };

  const initializeCameraWithMode = async (mode: 'environment' | 'user') => {
    const tryGetStream = async (constraints: MediaStreamConstraints) =>
      navigator.mediaDevices.getUserMedia(constraints);

    let stream: MediaStream;
    try {
      stream = await tryGetStream({ video: { facingMode: { ideal: mode } }, audio: false });
    } catch {
      try {
        stream = await tryGetStream({ video: true, audio: false });
      } catch (fallbackErr: unknown) {
        const errorName = (fallbackErr as Error)?.name || '';
        if (errorName === 'NotAllowedError' || errorName === 'PermissionDeniedError') {
          setCameraErrorType('permission');
        } else if (errorName === 'NotFoundError' || errorName === 'DevicesNotFoundError') {
          setCameraErrorType('notfound');
        } else {
          setCameraErrorType('generic');
        }
        setCameraError(true);
        return;
      }
    }

    streamRef.current = stream;
    if (videoRef.current) {
      videoRef.current.srcObject = stream;
    }
    setCameraError(false);
    setCameraErrorType(null);
    setReadiness('positioning');
  };

  // Uses the current facing mode (via ref to avoid stale closure)
  const initializeCamera = () => initializeCameraWithMode(facingModeRef.current);

  // Switch front/back camera — stops current stream then re-initialises
  const flipCamera = async () => {
    const next: 'environment' | 'user' = facingModeRef.current === 'environment' ? 'user' : 'environment';
    setFacingMode(next);
    facingModeRef.current = next;
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;
    setReadiness('initializing');
    readinessFiredRef.current = false;
    await initializeCameraWithMode(next);
  };

  const startRecording = () => {
    if (!streamRef.current) {
      toast({
        title: 'Camera Error',
        description: 'Camera not available. Please try again.',
        variant: 'destructive',
      });
      return;
    }

    try {
      recordedChunksRef.current = [];
      recordingStartTimeRef.current = Date.now();
      // Pick the best supported MIME type. iOS Safari only supports video/mp4;
      // forcing video/webm would silently record unusable data.
      const preferredTypes = [
        'video/mp4;codecs=avc1,mp4a.40.2',
        'video/mp4',
        'video/webm;codecs=vp9,opus',
        'video/webm;codecs=vp8,opus',
        'video/webm',
      ];
      const mimeType = preferredTypes.find((t) => MediaRecorder.isTypeSupported(t)) ?? '';
      mediaRecorderRef.current = new MediaRecorder(streamRef.current, mimeType ? { mimeType } : undefined);
      // Read back the actual type chosen by the browser (may differ from what we passed)
      recordingMimeRef.current = mediaRecorderRef.current.mimeType || mimeType || 'video/webm';

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = handleRecordingComplete;
      mediaRecorderRef.current.start();

      setRecordingState('recording');
      setRecordingTime(0);
      logBetaEvent('recording_started', { exercise: currentExercise });
    } catch (error) {
      console.error('Recording failed:', error);
      toast({
        title: 'Recording Error',
        description: 'Failed to start recording. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  };

  const handleRecordingComplete = async () => {
    if (recordedChunksRef.current.length === 0) {
      toast({
        title: 'Recording Error',
        description: 'No video data captured. Please try again.',
        variant: 'destructive',
      });
      setRecordingState('ready');
      return;
    }

    // Measure actual elapsed recording time
    const elapsedSec = recordingStartTimeRef.current
      ? (Date.now() - recordingStartTimeRef.current) / 1000
      : recordingTime;

    if (elapsedSec < MIN_RECORD_SECONDS) {
      // Clip is too short — discard and show validation error
      recordedChunksRef.current = [];
      recordingBlobRef.current = null;
      setTooShortError(true);
      setRecordingState('ready');
      return;
    }

    logBetaEvent('recording_completed', { exercise: currentExercise, duration_sec: Math.round(elapsedSec * 10) / 10 });

    // Build blob and preview URL using the actual recorded MIME type
    const actualMime = recordingMimeRef.current;
    const videoBlob = new Blob(recordedChunksRef.current, { type: actualMime });
    recordingBlobRef.current = videoBlob;
    const url = URL.createObjectURL(videoBlob);
    previewUrlRef.current = url;
    setRecordingState('preview');
  };

  const handleUseThisRep = async () => {
    if (!recordingBlobRef.current) return;

    // Build File from the blob — keep recordingBlobRef.current alive for potential retry
    const actualMime = recordingMimeRef.current;
    const ext = actualMime.startsWith('video/mp4') ? 'mp4' : 'webm';
    const videoFile = new File(
      [recordingBlobRef.current],
      `form-analysis-${Date.now()}.${ext}`,
      { type: actualMime }
    );

    // Revoke preview URL only — blob is kept for retry
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }
    recordedChunksRef.current = [];

    setRecordingState('uploading');
    setUploadError(null);
    setUploadProgress({ stage: 'uploading', progress: 5, message: 'Uploading video…' });

    // Jump to 40% immediately then creep slowly — reduces re-renders during upload
    let simulatedProgress = 40;
    setUploadProgress({ stage: 'uploading', progress: simulatedProgress, message: 'Uploading video…' });
    const progressInterval = setInterval(() => {
      simulatedProgress = Math.min(simulatedProgress + 5, 85);
      setUploadProgress({ stage: 'uploading', progress: simulatedProgress, message: 'Uploading video…' });
    }, 2000);

    // 60-second wall-clock timeout — triggers error state if server doesn't respond
    uploadSucceededRef.current = false;
    uploadTimeoutRef.current = setTimeout(() => {
      if (!uploadSucceededRef.current) {
        clearInterval(progressInterval);
        logEvent('upload_timeout', { exercise: currentExercise });
        setUploadProgress(null);
        setUploadError('Upload is taking too long. Check your connection and try again.');
        setRecordingState('error');
      }
    }, 60000);

    try {
      const weight_kg = weightLb ? Math.round(parseFloat(weightLb) * 0.453592 * 10) / 10 : undefined;
      const formCheck = await formCheckService.submitFormCheck(
        videoFile,
        currentExercise,
        undefined,
        shadowMode ? 'shadow' : 'active',
        weight_kg,
      );
      uploadSucceededRef.current = true;
      clearInterval(progressInterval);
      if (uploadTimeoutRef.current) clearTimeout(uploadTimeoutRef.current);
      recordingBlobRef.current = null; // safe to clear now that upload succeeded
      setFormCheckId(formCheck.id);
      setUploadProgress({ stage: 'processing', progress: 100, message: 'Submitted! Redirecting…' });
      logBetaEvent('analysis_requested', { exercise: currentExercise, source: 'camera' });
      navigate(`/analysis/${formCheck.id}`);
    } catch (error) {
      if (uploadSucceededRef.current) return; // timeout already handled this
      clearInterval(progressInterval);
      if (uploadTimeoutRef.current) clearTimeout(uploadTimeoutRef.current);
      console.error('Form check submission failed:', error);
      logEvent('upload_failed', { error: String(error) });
      setUploadProgress(null);
      setUploadError('Upload failed. Check your connection and try again.');
      setRecordingState('error');
    }
  };

  const handleRetake = () => {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }
    recordingBlobRef.current = null;
    recordedChunksRef.current = [];
    setRecordingState('ready');
  };

  // Called from the error screen — discards the failed blob and returns to camera
  const handleReRecord = () => {
    recordingBlobRef.current = null;
    recordedChunksRef.current = [];
    setUploadError(null);
    setUploadProgress(null);
    setRecordingState('ready');
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Reset input so the same file can be re-selected later
    if (fileInputRef.current) fileInputRef.current.value = '';

    // ── Pre-submit validation ─────────────────────────────────────────────
    // Allow empty MIME type — some Android browsers report '' for valid videos.
    if (file.type !== '' && !file.type.startsWith('video/')) {
      setUploadError('Please select a video file.');
      setRecordingState('error');
      return;
    }
    if (file.size > 500 * 1024 * 1024) {
      setUploadError('File too large. Trim your clip and try again.');
      setRecordingState('error');
      return;
    }
    // Read duration — if metadata read fails or times out, proceed and let backend validate.
    try {
      const dur = await getVideoDuration(file);
      if (dur < 2) {
        setUploadError('Clip too short — upload the full squat rep from start to finish.');
        setRecordingState('error');
        return;
      }
      if (dur > 8) {
        // > 30 s gets the multi-rep message; 8–30 s gets the "too long" message.
        setUploadError(
          dur > 30
            ? 'Upload one rep only — longer clips or multi-rep sets produce unreliable scores.'
            : 'This clip is too long. Upload one squat rep between 3 and 6 seconds.',
        );
        setRecordingState('error');
        return;
      }
    } catch {
      // Could not read metadata (timeout or unsupported format) — let backend validate.
    }

    setRecordingState('uploading');
    setUploadProgress({ stage: 'uploading', progress: 10, message: 'Uploading video…' });

    // Simulate progress creep (same pattern as camera upload)
    let simulatedProgress = 20;
    const progressInterval = setInterval(() => {
      simulatedProgress = Math.min(simulatedProgress + 4, 85);
      setUploadProgress({ stage: 'uploading', progress: simulatedProgress, message: 'Uploading video…' });
    }, 2000);

    // 60-second timeout guard
    let uploadSucceeded = false;
    const timeoutId = setTimeout(() => {
      if (!uploadSucceeded) {
        clearInterval(progressInterval);
        logEvent('upload_timeout', { exercise: currentExercise });
        setUploadProgress(null);
        setUploadError('Upload is taking too long. Check your connection and try again.');
        setRecordingState('error');
      }
    }, 60000);

    try {
      const weight_kg = weightLb ? Math.round(parseFloat(weightLb) * 0.453592 * 10) / 10 : undefined;
      const formCheck = await formCheckService.submitFormCheck(
        file,
        currentExercise,
        undefined,
        shadowMode ? 'shadow' : 'active',
        weight_kg,
      );
      uploadSucceeded = true;
      clearInterval(progressInterval);
      clearTimeout(timeoutId);
      setFormCheckId(formCheck.id);
      logBetaEvent('analysis_requested', { exercise: currentExercise, source: 'file_upload' });
      navigate(`/analysis/${formCheck.id}`);
    } catch (error) {
      if (uploadSucceeded) return;
      clearInterval(progressInterval);
      clearTimeout(timeoutId);
      console.error('File upload failed:', error);
      logEvent('upload_failed', { error: String(error) });
      setUploadProgress(null);
      setUploadError('Upload failed. Check your connection and try again.');
      setRecordingState('error');
    }
  };

  const handleSetupCheck = (item: keyof typeof setupChecklist) => {
    setSetupChecklist((prev) => ({ ...prev, [item]: !prev[item] }));

    // Auto-advance to next step
    const completedSteps = Object.values({
      ...setupChecklist,
      [item]: !setupChecklist[item],
    }).filter(Boolean).length;
    setCurrentSetupStep(Math.min(completedSteps, setupSteps.length - 1));
  };

  const startCountdown = async () => {
    // If camera stream is not available, attempt one more initialisation
    if (!streamRef.current) {
      await initializeCamera();
      if (!streamRef.current) return;
    }
    setCountdown(3);
    setRecordingState('countdown');
  };

  const cancelCountdown = () => {
    setRecordingState('ready');
    setCountdown(3);
  };

  // Count-up animation for completion screen
  useEffect(() => {
    if (recordingState !== 'complete') return;
    const target = formScore || 87;
    const duration = 800;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min((now - start) / duration, 1);
      setDisplayedScore(Math.round(t * target));
      if (t < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [recordingState, formScore]);

  const resetRecording = () => {
    setRecordingState('setup');
    setRecordingTime(0);
    setUploadProgress(null);
    setFormCheckId(null);
    setFormScore(null);
    setDisplayedScore(0);
    setCurrentSetupStep(0);
    setTooShortError(false);
    setWeightLb('');
    setSetupChecklist({
      angle: false,
      distance: false,
      lighting: false,
      visibility: false,
      stability: false,
    });
    recordedChunksRef.current = [];
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getSetupItemClass = (index: number, completed: boolean) => {
    if (completed) return 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800';
    if (index === currentSetupStep) return 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800';
    return 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700';
  };

  // ─── Screen renderers ─────────────────────────────────────────────────────

  const renderSetupScreen = () => (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.4, ease: 'easeInOut' }}
      className="space-y-8"
    >
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">Form Analysis</h2>
        <p className="text-gray-500 dark:text-gray-400 text-sm">Side view · full body visible · 1 rep · 3–6 sec</p>
      </div>

      <div className="space-y-3">
        <div className="flex items-center space-x-2">
          <Target className="w-5 h-5 text-blue-600" />
          <h3 className="font-semibold text-gray-900 dark:text-white">Select Exercise</h3>
        </div>
        {/* Supported exercises — selectable cards */}
        <div className="grid grid-cols-2 gap-3">
          {EXERCISE_OPTIONS.filter(e => e.supported).map((exercise) => (
            <Card
              key={exercise.value}
              className={`cursor-pointer transition-all duration-200 border-2 ${
                currentExercise === exercise.value
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                  : 'border-gray-200 dark:border-gray-700 hover:border-blue-300'
              }`}
              onClick={() => setCurrentExercise(exercise.value)}
            >
              <CardContent className="p-3 text-center">
                <p
                  className={`font-medium text-sm ${
                    currentExercise === exercise.value
                      ? 'text-blue-700 dark:text-blue-300'
                      : 'text-gray-900 dark:text-white'
                  }`}
                >
                  {exercise.label}
                </p>
                <Badge
                  variant="secondary"
                  className="mt-1 text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                >
                  AI Scoring
                </Badge>
              </CardContent>
            </Card>
          ))}
        </div>
        {/* Unsupported exercises — plain coming-soon list */}
        <div className="space-y-1 pt-1">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Coming soon</p>
          <p className="text-xs text-muted-foreground">
            {EXERCISE_OPTIONS.filter(e => !e.supported).map(e => e.label).join(' · ')}
          </p>
        </div>
        {process.env.REACT_APP_DEV_TOOLS === 'true' && (
          <label className="flex items-center space-x-2 mt-2 text-xs text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={shadowMode}
              onChange={(e) => setShadowMode(e.target.checked)}
              className="rounded border-gray-300"
            />
            <span>Shadow mode (dev)</span>
          </label>
        )}
      </div>

      {/* Optional weight entry */}
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">Weight used (optional)</h3>
        <div className="space-y-1">
          <label className="text-sm text-gray-600 dark:text-gray-400">Weight (lb)</label>
          <input
            type="number"
            min={0}
            step={5}
            placeholder="e.g. 225"
            value={weightLb}
            onChange={(e) => setWeightLb(e.target.value)}
            className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="space-y-3">
        {setupSteps.map((item, index) => (
          <motion.div
            key={item.key}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1, duration: 0.3 }}
          >
            <Card
              className={`cursor-pointer transition-all duration-300 border-2 ${getSetupItemClass(index, setupChecklist[item.key])}`}
              onClick={() => handleSetupCheck(item.key)}
            >
              <CardContent className="p-4">
                <div className="flex items-center space-x-4">
                  <div
                    className={`w-12 h-12 rounded-lg flex items-center justify-center transition-all duration-300 ${
                      setupChecklist[item.key]
                        ? 'bg-green-500 text-white shadow-lg'
                        : index === currentSetupStep
                          ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600'
                          : 'bg-gray-200 dark:bg-gray-700 text-gray-400'
                    }`}
                  >
                    {setupChecklist[item.key] ? (
                      <CheckCircle className="w-6 h-6" />
                    ) : (
                      <item.icon className="w-4 h-4" />
                    )}
                  </div>
                  <div className="flex-1">
                    <h4
                      className={`font-medium transition-colors duration-300 ${
                        setupChecklist[item.key]
                          ? 'text-green-900 dark:text-green-100'
                          : 'text-gray-900 dark:text-white'
                      }`}
                    >
                      {item.label}
                    </h4>
                    <p
                      className={`text-sm transition-colors duration-300 ${
                        setupChecklist[item.key]
                          ? 'text-green-700 dark:text-green-300'
                          : 'text-gray-600 dark:text-gray-400'
                      }`}
                    >
                      {item.description}
                    </p>
                  </div>
                  {index === currentSetupStep && !setupChecklist[item.key] && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="w-3 h-3 bg-blue-500 rounded-full animate-pulse"
                    />
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <Button
        onClick={() => setRecordingState('ready')}
        className="w-full"
        size="lg"
      >
        <Camera className="w-4 h-4 mr-2" />
        Start Recording
      </Button>

      {/* Alternative: upload a pre-recorded file */}
      <div className="text-center">
        <p className="text-sm text-gray-400 dark:text-gray-500 mb-3">— or —</p>
        <input
          ref={fileInputRef}
          type="file"
          accept="video/*"
          className="hidden"
          onChange={handleFileUpload}
        />
        <p className="text-xs text-muted-foreground mb-2">
          One squat rep · 3–6 sec · full body visible
        </p>
        <Button
          variant="outline"
          onClick={() => fileInputRef.current?.click()}
          className="w-full"
          size="lg"
        >
          <Upload className="w-4 h-4 mr-2" />
          Upload Video
        </Button>
      </div>
    </motion.div>
  );

  const renderReadyScreen = () => (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.4, ease: 'easeInOut' }}
      className="space-y-6"
    >
      <div className="text-center">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-1">Ready to Record</h2>
        <p className="text-gray-500 dark:text-gray-400 text-sm">Tap the button when you're in position</p>
      </div>

      {/* "Clip too short" validation banner */}
      {tooShortError && (
        <div className="rounded-lg border border-orange-300 bg-orange-50 dark:bg-orange-900/20 dark:border-orange-700 p-3 flex items-start justify-between">
          <div className="flex items-start space-x-2">
            <AlertTriangle className="w-4 h-4 text-orange-600 dark:text-orange-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-orange-800 dark:text-orange-200">Clip too short</p>
              <p className="text-xs text-orange-700 dark:text-orange-300 mt-0.5">
                Record the full rep from start to finish (3–6 seconds).
              </p>
            </div>
          </div>
          <button
            onClick={() => setTooShortError(false)}
            className="text-orange-500 hover:text-orange-700 dark:text-orange-400 dark:hover:text-orange-200 ml-2 flex-shrink-0"
            aria-label="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {cameraError ? (
        <Card className="bg-red-50/60 dark:bg-red-900/10 border border-red-200 dark:border-red-800">
          <CardContent className="p-6 text-center">
            <Camera className="w-10 h-10 mx-auto mb-3 text-red-400" />
            <h3 className="font-semibold text-red-700 dark:text-red-300 mb-2">Could not access camera</h3>
            <p className="text-sm text-red-600 dark:text-red-400 mb-4">{getCameraErrorMessage()}</p>
            {cameraErrorType !== 'permission' && (
              <Button onClick={initializeCamera} variant="outline" className="border-red-200 text-red-600 bg-transparent">
                Try Again
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="relative aspect-video bg-black rounded-2xl overflow-hidden shadow-2xl">
          <video ref={videoRef} autoPlay muted playsInline className="w-full h-full object-cover" />

          {/* Framing guide — corner brackets */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <motion.div
              animate={{ opacity: readiness === 'ready' ? [0.5, 0.85, 0.5] : [0.25, 0.45, 0.25] }}
              transition={{ duration: 3, repeat: Number.POSITIVE_INFINITY }}
              className="relative w-28 h-56"
            >
              <div className={`absolute top-0 left-0 w-5 h-5 border-t-2 border-l-2 ${readiness === 'ready' ? 'border-green-400' : 'border-white/70'}`} />
              <div className={`absolute top-0 right-0 w-5 h-5 border-t-2 border-r-2 ${readiness === 'ready' ? 'border-green-400' : 'border-white/70'}`} />
              <div className={`absolute bottom-0 left-0 w-5 h-5 border-b-2 border-l-2 ${readiness === 'ready' ? 'border-green-400' : 'border-white/70'}`} />
              <div className={`absolute bottom-0 right-0 w-5 h-5 border-b-2 border-r-2 ${readiness === 'ready' ? 'border-green-400' : 'border-white/70'}`} />
              <div className="absolute inset-0 flex flex-col items-center justify-end pb-3">
                <span className="text-white/80 text-[10px] font-medium bg-black/50 px-2 py-0.5 rounded">Full body here</span>
              </div>
            </motion.div>
          </div>

          {/* Dynamic readiness banner */}
          <div className="absolute top-3 left-3 right-3 flex items-center justify-between">
            <motion.div
              key={readiness}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold shadow-sm ${
                readiness === 'ready'
                  ? 'bg-green-500/90 text-white'
                  : readiness === 'positioning'
                    ? 'bg-amber-500/85 text-white'
                    : 'bg-black/60 text-white/70'
              }`}
            >
              {readiness === 'ready' && <CheckCircle className="w-3 h-3 flex-shrink-0" />}
              {readiness === 'positioning' && <span className="w-2 h-2 rounded-full bg-white/90 animate-pulse flex-shrink-0" />}
              <span>
                {readiness === 'ready'
                  ? 'Ready ✓'
                  : readiness === 'positioning'
                    ? 'Position yourself — side view, full body'
                    : 'Starting camera…'}
              </span>
            </motion.div>

            {/* Camera flip toggle */}
            <button
              onClick={flipCamera}
              className="p-2 rounded-full bg-black/50 text-white/80 hover:bg-black/70 active:scale-95 transition-all"
              aria-label={facingMode === 'environment' ? 'Switch to front camera' : 'Switch to back camera'}
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>

          {/* Record Button */}
          <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2">
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 1.05 }}
              onClick={startCountdown}
              className="w-20 h-20 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full flex items-center justify-center shadow-2xl"
              aria-label="Start recording"
            >
              <Video className="w-10 h-10 text-white" />
            </motion.button>
          </div>
        </div>
      )}

      <p className="text-xs text-center text-muted-foreground">
        {facingMode === 'environment'
          ? 'Back camera · recommended for best analysis'
          : 'Front camera · back camera gives better results'}
      </p>

      <Button
        onClick={() => setRecordingState('setup')}
        variant="outline"
        size="sm"
        className="w-full flex items-center justify-center"
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Setup
      </Button>
    </motion.div>
  );

  const renderUploadingScreen = () => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4, ease: 'easeInOut' }}
      className="space-y-8"
    >
      <div className="text-center">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY, ease: 'linear' }}
          className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center mx-auto mb-6 shadow-xl"
        >
          <Upload className="w-8 h-8 text-white" />
        </motion.div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">Uploading Video</h2>
        <p className="text-gray-600 dark:text-gray-400">Preparing your video for AI analysis...</p>
      </div>

      {uploadProgress && (
        <div className="space-y-4">
          <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
            <span>{uploadProgress.message}</span>
            <span className="font-semibold">{Math.round(uploadProgress.progress)}%</span>
          </div>
          <Progress value={uploadProgress.progress} className="h-4" />
        </div>
      )}
    </motion.div>
  );

  const renderUploadErrorScreen = () => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4, ease: 'easeInOut' }}
      className="space-y-8"
    >
      <div className="text-center">
        <div className="w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mx-auto mb-6">
          <AlertTriangle className="w-8 h-8 text-red-500 dark:text-red-400" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">Upload Failed</h2>
        <p className="text-gray-600 dark:text-gray-400">
          {uploadError || 'Something went wrong. Check your connection and try again.'}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {recordingBlobRef.current ? (
          <>
            <Button onClick={handleReRecord} variant="outline" className="flex items-center justify-center">
              <RotateCcw className="w-4 h-4 mr-2" />
              Re-record
            </Button>
            <Button
              onClick={handleUseThisRep}
              className="flex items-center justify-center bg-blue-600 hover:bg-blue-700 text-white"
            >
              <Upload className="w-4 h-4 mr-2" />
              Retry Upload
            </Button>
          </>
        ) : (
          <>
            <Button
              onClick={handleReRecord}
              variant="outline"
              className="flex items-center justify-center"
            >
              <Camera className="w-4 h-4 mr-2" />
              Record Instead
            </Button>
            <Button
              onClick={() => { setUploadError(null); setRecordingState('setup'); setTimeout(() => fileInputRef.current?.click(), 50); }}
              className="flex items-center justify-center bg-blue-600 hover:bg-blue-700 text-white"
            >
              <Upload className="w-4 h-4 mr-2" />
              Try Another File
            </Button>
          </>
        )}
      </div>
    </motion.div>
  );

  const renderCompleteScreen = () => (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.1 }}
      transition={{ duration: 0.4, ease: 'easeInOut' }}
      className="space-y-8"
    >
      <div className="text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 200 }}
          className="w-16 h-16 bg-gradient-to-r from-green-500 to-emerald-600 rounded-full flex items-center justify-center mx-auto mb-6 shadow-xl"
        >
          <CheckCircle className="w-8 h-8 text-white" />
        </motion.div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">Analysis Complete!</h2>
        <p className="text-gray-600 dark:text-gray-400">Your form has been analyzed by AI</p>
      </div>

      <Card className="bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20">
        <CardContent className="p-8">
          <div className="text-center">
            <div className="text-5xl font-bold text-green-600 mb-2">{displayedScore}%</div>
            <p className="text-gray-600 dark:text-gray-400 mb-4">Overall Form Score</p>
            <Badge className="bg-green-500 text-white">
              {(formScore || 87) >= 85 ? 'Great Job!' : (formScore || 87) >= 70 ? 'Good Work!' : 'Keep Practicing!'}
            </Badge>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-4">
        <Button onClick={resetRecording} variant="outline" className="flex items-center">
          <RotateCcw className="w-4 h-4 mr-2" />
          Record Again
        </Button>
        <Button
          onClick={() => formCheckId ? navigate(`/analysis/${formCheckId}`) : navigate('/analysis')}
          className="flex items-center"
        >
          <Play className="w-4 h-4 mr-2" />
          View Analysis
        </Button>
      </div>
    </motion.div>
  );

  // ─── Full-screen overlays (countdown, recording, preview) ────────────────

  const renderCountdownOverlay = () => (
    <div className="fixed inset-0 bg-black z-50">
      {/* Cancel */}
      <button
        onClick={cancelCountdown}
        className="absolute top-4 right-4 z-10 p-2 rounded-full bg-white/20 hover:bg-white/30 text-white transition-colors"
        aria-label="Cancel countdown"
      >
        <X className="w-6 h-6" />
      </button>

      {/* Camera feed */}
      <video ref={videoRef} autoPlay muted playsInline className="absolute inset-0 w-full h-full object-cover" />

      {/* Countdown overlay */}
      <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/50">
        <AnimatePresence mode="wait">
          <motion.div
            key={countdown}
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 1.5, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className={`font-bold text-white text-center ${countdown === 0 ? 'text-6xl' : 'text-9xl'}`}
          >
            {countdown === 0 ? 'Go!' : countdown}
          </motion.div>
        </AnimatePresence>
        <p className="text-white text-xl font-medium mt-4">
          {countdown === 0 ? 'Perform one controlled squat rep!' : 'Get ready to move'}
        </p>
      </div>
    </div>
  );

  const renderRecordingOverlay = () => (
    <div className="fixed inset-0 bg-black z-50">
      {/* Camera feed */}
      <video ref={videoRef} autoPlay muted playsInline className="absolute inset-0 w-full h-full object-cover" />

      {/* Top: REC indicator + timer */}
      <div className="absolute top-0 left-0 right-0 px-4 pt-4 flex items-center justify-between">
        <Badge className="bg-red-500 text-white animate-pulse shadow-lg">
          <div className="w-2 h-2 bg-white rounded-full mr-2" />
          REC
        </Badge>
        <Badge variant="outline" className="bg-black/50 text-white border-white/30">
          <Timer className="w-3 h-3 mr-1" />
          {formatTime(recordingTime)}
        </Badge>
      </div>

      {/* Bottom hint */}
      <div className="absolute bottom-28 left-4 right-4">
        <div className="bg-black/60 rounded-lg p-3 text-center">
          <p className="text-white text-sm font-medium">Perform one controlled rep.</p>
        </div>
      </div>

      {/* Stop button — large, thumb-reachable */}
      <div
        className="absolute left-0 right-0 flex justify-center"
        style={{ bottom: 'max(calc(env(safe-area-inset-bottom) + 24px), 24px)' }}
      >
        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={stopRecording}
          className="w-20 h-20 bg-red-600 hover:bg-red-700 rounded-full flex items-center justify-center shadow-2xl"
          aria-label="Stop recording"
        >
          <Square className="w-8 h-8 text-white" />
        </motion.button>
      </div>
    </div>
  );

  const renderPreviewOverlay = () => (
    <div className="fixed inset-0 bg-black z-50 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-12 pb-2 flex-shrink-0">
        <p className="text-base font-semibold text-white">Review your clip</p>
        <span className="text-xs text-white/50 bg-white/10 px-2 py-0.5 rounded-full">Squat · 1 rep</span>
      </div>

      {/* Confirmation body */}
      <div className="flex-1 flex flex-col items-center justify-center px-8 text-center gap-4">
        <div className="w-20 h-20 rounded-full bg-white/10 flex items-center justify-center">
          <CheckCircle className="w-10 h-10 text-white/70" />
        </div>
        <div className="space-y-2">
          <p className="text-white font-medium text-lg leading-snug">
            Does this show one full squat rep from start to finish (no rerack or unrack)?
          </p>
          <p className="text-white/50 text-sm">
            Make sure your full body is visible from the side.
          </p>
        </div>
      </div>

      {/* Action buttons */}
      <div
        className="px-5 pt-4 flex-shrink-0"
        style={{ paddingBottom: 'max(calc(env(safe-area-inset-bottom) + 16px), 24px)' }}
      >
        <Button
          size="lg"
          className="w-full h-14 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl text-base mb-3"
          onClick={handleUseThisRep}
        >
          Use this rep
        </Button>
        <Button
          size="lg"
          variant="outline"
          className="w-full h-12 border-white/30 text-white bg-transparent hover:bg-white/10 font-medium rounded-xl text-base"
          onClick={handleRetake}
        >
          <RotateCcw className="w-4 h-4 mr-2" />
          Re-record
        </Button>
      </div>
    </div>
  );

  const getCurrentScreen = () => {
    switch (recordingState) {
      case 'setup':
        return renderSetupScreen();
      case 'ready':
        return renderReadyScreen();
      case 'uploading':
        return renderUploadingScreen();
      case 'error':
        return renderUploadErrorScreen();
      case 'complete':
        return renderCompleteScreen();
      default:
        return renderSetupScreen();
    }
  };

  const isFullscreenState = recordingState === 'countdown' || recordingState === 'recording' || recordingState === 'preview';

  return (
    <AppLayout showBottomNav={!isFullscreenState}>
      {/* Card content — hidden during full-screen recording/preview states */}
      {!isFullscreenState && (
        <div className="px-4 py-6 max-w-2xl mx-auto" style={{ paddingBottom: 'max(calc(env(safe-area-inset-bottom) + 64px), 96px)' }}>
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/')}
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Form Analysis</h1>
            <div className="w-16" />
          </div>

          {/* Content */}
          <Card className="shadow-xl border-0 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm">
            <CardContent className="p-8">
              <AnimatePresence mode="wait">
                <motion.div key={recordingState}>
                  {getCurrentScreen()}
                </motion.div>
              </AnimatePresence>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Full-screen overlays */}
      {recordingState === 'countdown' && renderCountdownOverlay()}
      {recordingState === 'recording' && renderRecordingOverlay()}
      {recordingState === 'preview' && renderPreviewOverlay()}
    </AppLayout>
  );
}
