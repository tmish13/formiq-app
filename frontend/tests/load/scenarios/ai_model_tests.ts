import { check, group } from 'k6';
import http from 'k6/http';
import { Trend, Rate } from 'k6/metrics';
import { Options } from 'k6/options';
import { sleep } from 'k6';

// Custom metrics
const modelConfidence = new Trend('model_confidence');
const modelLatency = new Trend('model_latency');
const fallbackRate = new Rate('fallback_rate');
const errorRate = new Rate('error_rate');

export const options: Options = {
  scenarios: {
    model_stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 50 },  // Ramp up
        { duration: '5m', target: 50 },  // Stay at peak
        { duration: '2m', target: 0 }    // Ramp down
      ],
      gracefulRampDown: '30s'
    },
    concurrent_analysis: {
      executor: 'constant-arrival-rate',
      rate: 30,                 // 30 iterations per timeUnit
      timeUnit: '1m',          // 1 minute
      duration: '10m',         // 10 minutes
      preAllocatedVUs: 50,
      maxVUs: 100
    },
    error_injection: {
      executor: 'shared-iterations',
      vus: 10,
      iterations: 100,
      startTime: '0s'
    }
  },
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests should be below 2s
    http_req_failed: ['rate<0.01'],    // Error rate should be below 1%
    'model_confidence': ['avg>0.8'],    // Average model confidence should be above 80%
    'model_latency': ['p(90)<5000']    // 90% of model inferences should be under 5s
  }
};

interface AnalysisResponse {
  id: string;
  status: string;
  confidence: number;
  feedback: string;
  usedFallback: boolean;
  poses: any[];
  timestamp: number;
}

class FormAnalysisAPI {
  private baseUrl: string;
  private token: string;

  constructor() {
    this.baseUrl = __ENV.API_URL || 'http://localhost:3000/api/v1';
    this.token = '';
  }

  async login(): Promise<void> {
    const response = await http.post(`${this.baseUrl}/auth/login`, {
      email: `loadtest${__VU}@example.com`,
      password: 'testpassword123'
    });

    if (response.status === 200) {
      this.token = response.json('tokens').accessToken;
    }
  }

  async submitFormAnalysis(
    exerciseType: string,
    quality: string
  ): Promise<AnalysisResponse> {
    const headers = {
      'Authorization': `Bearer ${this.token}`,
      'Content-Type': 'multipart/form-data'
    };

    // Simulate video data based on quality
    const videoData = this.getTestVideo(quality);
    
    const response = await http.post(
      `${this.baseUrl}/form-analysis/analyze`,
      {
        video: videoData,
        exerciseType,
        quality
      },
      { headers }
    );

    const result = response.json() as AnalysisResponse;
    
    // Record metrics
    modelConfidence.add(result.confidence);
    if (result.usedFallback) {
      fallbackRate.add(1);
    }

    return result;
  }

  private getTestVideo(quality: string): ArrayBuffer {
    // Simulate different video qualities
    const videoSizes = {
      low: 1024 * 1024,      // 1MB
      medium: 5 * 1024 * 1024,  // 5MB
      high: 10 * 1024 * 1024,   // 10MB
      corrupted: 100,           // Corrupted data
      empty: 0                  // Empty data
    };

    const size = videoSizes[quality] || videoSizes.medium;
    return new ArrayBuffer(size);
  }
}

// Main test function
export default function() {
  const api = new FormAnalysisAPI();
  
  group('setup', async () => {
    await api.login();
  });

  // Test different exercise types
  const exercises = ['squat', 'deadlift', 'bench_press', 'pullup'];
  const exercise = exercises[Math.floor(Math.random() * exercises.length)];
  
  // Test with different video qualities
  const videoQualities = ['low', 'medium', 'high'];
  const quality = videoQualities[Math.floor(Math.random() * videoQualities.length)];
  
  group('concurrent_analysis', async () => {
    try {
      // Submit multiple analyses in parallel
      const promises = [];
      for (let i = 0; i < 3; i++) {
        promises.push(api.submitFormAnalysis(exercise, quality));
      }
      const results = await Promise.all(promises);
      
      // Verify all requests succeeded
      check(results, {
        'all_requests_completed': (r) => r.length === 3,
        'all_requests_successful': (r) => r.every(res => res.status === 'completed')
      });
    } catch (e) {
      errorRate.add(1);
      console.error('Concurrent analysis failed:', e);
    }
  });
  
  group('error_handling', async () => {
    try {
      // Test with invalid video format
      const invalidResult = await api.submitFormAnalysis(exercise, 'invalid');
      check(invalidResult, {
        'invalid_format_handled': (r) => r.status === 'error' && r.feedback.includes('format')
      });
      
      // Test with empty video
      const emptyResult = await api.submitFormAnalysis(exercise, 'empty');
      check(emptyResult, {
        'empty_video_handled': (r) => r.status === 'error' && r.feedback.includes('empty')
      });
      
      // Test with corrupted video
      const corruptedResult = await api.submitFormAnalysis(exercise, 'corrupted');
      check(corruptedResult, {
        'corrupted_video_handled': (r) => r.status === 'error' && r.feedback.includes('corrupted')
      });
    } catch (e) {
      errorRate.add(1);
      console.error('Error handling test failed:', e);
    }
  });
  
  group('performance_validation', async () => {
    try {
      const startTime = Date.now();
      const result = await api.submitFormAnalysis(exercise, 'high');
      const duration = Date.now() - startTime;
      
      modelLatency.add(duration);
      
      check(result, {
        'response_time_within_limit': () => duration < 5000,
        'confidence_above_threshold': (r) => r.confidence > 0.8
      });
    } catch (e) {
      errorRate.add(1);
      console.error('Performance validation failed:', e);
    }
  });

  // Add think time between iterations
  sleep(Math.random() * 3 + 1); // Random sleep between 1-4 seconds
} 