# Performance Load Testing Guide

This document explains how to run performance tests to validate FormIQ's resume claims:
- **99.9% API success rate under load**
- **100+ concurrent video uploads**
- **Sub-300ms frame processing**

## Prerequisites

1. **Install dependencies:**
   ```bash
   cd backend
   pip install locust pytest
   ```

2. **Create test videos:**
   ```bash
   cd backend/perf/test_fixtures
   python create_sample_video.py
   ```

3. **Start FormIQ services:**
   ```bash
   # Terminal 1: Start backend
   cd backend
   uvicorn app.main:app --host 0.0.0.0 --port 8000

   # Terminal 2: Start Celery worker
   cd backend  
   celery -A app.core.celery_app worker --loglevel=info

   # Terminal 3: Start monitoring (optional)
   cd infrastructure/docker
   docker-compose up prometheus jaeger -d
   ```

## Load Testing Scenarios

### 1. Basic Video Upload Load Test

Test 100+ concurrent users uploading videos:

```bash
cd backend/perf

# Run with Locust Web UI
locust -f locustfile_video_uploads.py --host=http://localhost:8000

# Open http://localhost:8089
# Configure: 150 users, spawn rate 10/sec, run for 5 minutes
```

**Expected Results:**
- Success rate: ≥ 99.9%
- P95 response time: < 2000ms for uploads
- P95 frame processing: < 300ms

### 2. High-Concurrency Stress Test

Test with aggressive load patterns:

```bash
# Headless mode for CI/CD
locust -f locustfile_video_uploads.py \
  --host=http://localhost:8000 \
  --users 200 \
  --spawn-rate 20 \
  --run-time 3m \
  --headless \
  --html results/stress_test_report.html
```

### 3. Realistic Usage Patterns

Test with realistic user behavior:

```bash
# Use RealisticUser class for normal usage patterns
locust -f locustfile_video_uploads.py \
  --host=http://localhost:8000 \
  --users 50 \
  --spawn-rate 5 \
  --run-time 10m \
  --user-classes RealisticUser
```

## Monitoring Performance During Tests

### 1. Real-time API Metrics

Check success rate during test:

```bash
# Check current success rate
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/metrics-analysis/success-rate"

# Check SLA compliance
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/metrics-analysis/sla-compliance"
```

### 2. Prometheus Queries

Use these queries in Prometheus (http://localhost:9090):

```promql
# API Success Rate (5-minute window)
sum(rate(http_requests_total{status=~"2.."}[5m])) / 
sum(rate(http_requests_total[5m])) * 100

# Frame Processing P95 Latency
histogram_quantile(0.95, 
  sum(rate(video_frame_processing_duration_seconds_bucket[5m])) by (le)
)

# Requests per Second
sum(rate(http_requests_total[5m]))

# Error Rate
sum(rate(http_requests_total{status=~"[45].."}[5m])) / 
sum(rate(http_requests_total[5m])) * 100
```

### 3. Jaeger Tracing

View distributed traces in Jaeger UI (http://localhost:16686):
- Search for traces by operation: `POST /api/v1/videos/upload`
- Filter by tags: `correlation_id:perf-test-*`
- Analyze request flow and bottlenecks

## Performance Targets & SLA Validation

### Success Rate Target: 99.9%

**Formula:** `(successful_requests / total_requests) * 100 ≥ 99.9`

**Validation:**
```bash
# Automated SLA check
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/metrics-analysis/sla-compliance" | \
  jq '.success_rate_compliant'
```

### Frame Processing Target: <300ms P95

**Formula:** `P95(frame_processing_duration) ≤ 300ms`

**Validation:**
```promql
histogram_quantile(0.95, 
  rate(video_frame_processing_duration_seconds_bucket[5m])
) * 1000 <= 300
```

### Concurrent Users Target: 100+

**Validation:**
- Locust should maintain 100+ active users
- Success rate should remain ≥99.9% throughout test
- No significant performance degradation

## Test Result Interpretation

### ✅ PASS Criteria

**API Success Rate:**
- Overall success rate ≥ 99.9%
- Per-endpoint success rate ≥ 99.0%
- Error rate ≤ 0.1%

**Performance:**
- P95 frame processing ≤ 300ms
- P95 API response time ≤ 2000ms
- Average response time ≤ 500ms

**Concurrency:**
- 100+ concurrent users sustained
- No memory leaks or resource exhaustion
- Consistent performance throughout test duration

### ❌ FAIL Criteria

**Any of the following indicates SLA failure:**
- Success rate < 99.9%
- Frame processing P95 > 300ms
- API response P95 > 5000ms
- Error rate > 0.5%
- System crashes or becomes unresponsive

## Automated Testing in CI/CD

### GitHub Actions Integration

Create `.github/workflows/performance_testing.yml`:

```yaml
name: Performance Testing
on:
  workflow_dispatch:  # Manual trigger
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Mondays

jobs:
  performance-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install locust
          
      - name: Start services
        run: |
          cd backend
          uvicorn app.main:app &
          celery -A app.core.celery_app worker &
          
      - name: Run performance test
        run: |
          cd backend/perf
          locust -f locustfile_video_uploads.py \
            --host=http://localhost:8000 \
            --users 100 \
            --spawn-rate 10 \
            --run-time 2m \
            --headless \
            --html performance_report.html
            
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: performance-test-results
          path: backend/perf/performance_report.html
```

## Troubleshooting

### Common Issues

**1. High Error Rates**
- Check database connections
- Verify Celery workers are running
- Monitor memory/CPU usage

**2. Slow Frame Processing**
- Check MediaPipe GPU acceleration
- Verify FFmpeg optimization settings
- Monitor disk I/O for temporary files

**3. Authentication Failures**
- Ensure test users can be created
- Check JWT token expiration
- Verify rate limiting settings

### Performance Optimization

**For Better Results:**
1. **Scale workers:** Increase Celery concurrency
2. **Optimize database:** Check connection pooling
3. **Tune caching:** Verify Redis performance
4. **Monitor resources:** Use Prometheus alerting

### Debug Commands

```bash
# Check system resources during test
top -p $(pgrep -f uvicorn)
htop

# Monitor database connections
psql -c "SELECT count(*) FROM pg_stat_activity;"

# Check Celery worker status
celery -A app.core.celery_app inspect active

# Real-time log monitoring
tail -f backend/logs/app.log
```

## Report Generation

After running tests, check the generated HTML report for:

1. **Request statistics** (success rate, response times)
2. **Performance charts** (users, RPS, response times)
3. **Error analysis** (failure types and frequencies)
4. **Custom metrics** (frame processing times)

The report will clearly indicate if resume claims are validated:
- ✅ **99.9% API Success Rate**: PASS/FAIL
- ✅ **100+ Concurrent Users**: PASS/FAIL  
- ✅ **Sub-300ms Frame Processing**: PASS/FAIL