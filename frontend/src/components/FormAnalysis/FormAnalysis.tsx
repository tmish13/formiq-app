import React, { useState, useRef, useCallback } from 'react';
import { formAnalysisService } from '../../services/formAnalysisService';
import { FormAnalysisResult, FormAnalysisRequest } from '../../types/formAnalysis';
import { Button, Card, Progress, Alert, Space, Upload, Typography } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import type { UploadRequestOption } from 'rc-upload/lib/interface';
import styles from './FormAnalysis.module.css';

const { Title, Text } = Typography;

export const FormAnalysis: React.FC = () => {
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<FormAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const handleVideoUpload = useCallback(async (options: UploadRequestOption) => {
    try {
      setAnalyzing(true);
      setError(null);
      setResult(null);

      const file = options.file as File;
      // Create video URL
      const videoUrl = URL.createObjectURL(file);

      // Wait for video metadata to load
      await new Promise<void>((resolve) => {
        if (videoRef.current) {
          videoRef.current.src = videoUrl;
          videoRef.current.onloadedmetadata = () => resolve();
        }
      });

      const request: FormAnalysisRequest = {
        videoUrl,
        keypoints: [], // Will be populated by pose analysis
        duration: videoRef.current?.duration || 0
      };

      const analysisResult = await formAnalysisService.analyzeForm(request);
      setResult(analysisResult);
      options.onSuccess?.(analysisResult);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to analyze form';
      setError(errorMessage);
      options.onError?.(new Error(errorMessage));
    } finally {
      setAnalyzing(false);
    }
  }, []);

  const renderResult = () => {
    if (!result) return null;

    return (
      <Card className={styles.resultCard}>
        <Title level={4}>Analysis Results</Title>
        
        <div className={styles.metricsGrid}>
          <div className={styles.metric}>
            <Text>Alignment</Text>
            <Progress 
              type="circle" 
              percent={Math.round(result.metrics.alignment * 100)} 
              status={result.metrics.alignment >= 0.7 ? 'success' : 'exception'}
            />
          </div>
          <div className={styles.metric}>
            <Text>Stability</Text>
            <Progress 
              type="circle" 
              percent={Math.round(result.metrics.stability * 100)}
              status={result.metrics.stability >= 0.7 ? 'success' : 'exception'}
            />
          </div>
          <div className={styles.metric}>
            <Text>Symmetry</Text>
            <Progress 
              type="circle" 
              percent={Math.round(result.metrics.symmetry * 100)}
              status={result.metrics.symmetry >= 0.7 ? 'success' : 'exception'}
            />
          </div>
          <div className={styles.metric}>
            <Text>Consistency</Text>
            <Progress 
              type="circle" 
              percent={Math.round(result.metrics.consistency * 100)}
              status={result.metrics.consistency >= 0.7 ? 'success' : 'exception'}
            />
          </div>
        </div>

        <div className={styles.feedback}>
          <Title level={5}>Feedback</Title>
          <ul>
            {result.feedback.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </div>

        <div className={styles.suggestions}>
          <Title level={5}>Suggestions</Title>
          <ul>
            {result.suggestions.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </div>
      </Card>
    );
  };

  return (
    <div className={styles.container}>
      <Card className={styles.uploadCard}>
        <Title level={3}>Form Analysis</Title>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {error && (
            <Alert
              message="Error"
              description={error}
              type="error"
              showIcon
              closable
              onClose={() => setError(null)}
            />
          )}

          <Upload
            accept="video/*"
            showUploadList={false}
            customRequest={handleVideoUpload}
            disabled={analyzing}
          >
            <Button 
              icon={<UploadOutlined />} 
              loading={analyzing}
              type="primary"
              size="large"
              block
            >
              {analyzing ? 'Analyzing...' : 'Upload Video'}
            </Button>
          </Upload>

          <div className={styles.preview}>
            <video
              ref={videoRef}
              className={styles.video}
              controls
              playsInline
              style={{ display: videoRef.current?.src ? 'block' : 'none' }}
            />
          </div>
        </Space>
      </Card>

      {result && renderResult()}
    </div>
  );
}; 