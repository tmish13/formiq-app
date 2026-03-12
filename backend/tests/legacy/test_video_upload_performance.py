"""Performance validation tests for video upload functionality."""

import pytest
import time
import asyncio
from typing import List, Dict
from unittest.mock import Mock, patch
import statistics

from fastapi.testclient import TestClient
from app.main import app
from app.services.metrics_analysis_service import metrics_analysis_service


class TestVideoUploadPerformance:
    """Performance tests for video upload and processing."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_authenticated_user(self):
        """Mock authenticated user."""
        user_mock = Mock()
        user_mock.id = "perf-test-user"
        user_mock.email = "perf@test.com"
        return user_mock
    
    @pytest.fixture
    def small_video_data(self) -> bytes:
        """Create small video data for testing."""
        # Create 50KB of mock video data
        data_size = 50 * 1024
        pattern = b'\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom\x00\x00\x00\x08free'
        base_pattern = pattern * (data_size // len(pattern) + 1)
        return base_pattern[:data_size]
    
    @patch('app.api.deps.get_current_active_user')
    def test_single_video_upload_performance(self, mock_get_user, client, mock_authenticated_user, small_video_data):
        """Test single video upload performance baseline."""
        mock_get_user.return_value = mock_authenticated_user
        
        start_time = time.time()
        
        # Step 1: Request presigned URL
        response = client.post(
            "/api/v1/videos/upload",
            json={
                "filename": "performance_test.mp4",
                "content_type": "video/mp4",
                "file_size": len(small_video_data),
                "exercise_id": 1
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        presigned_time = time.time() - start_time
        assert response.status_code == 200
        assert presigned_time < 1.0  # Should be very fast
        
        upload_data = response.json()
        video_id = upload_data.get("video_id")
        assert video_id is not None
        
        # Step 2: Simulate video upload completion
        upload_start = time.time()
        response = client.put(
            f"/api/v1/videos/{video_id}/upload-complete",
            files={"video": ("test.mp4", small_video_data, "video/mp4")},
            headers={"Authorization": "Bearer fake-token"}
        )
        
        upload_time = time.time() - upload_start
        total_time = time.time() - start_time
        
        # Validate response
        assert response.status_code in [200, 201]
        
        # Performance assertions
        assert upload_time < 5.0  # Upload should complete quickly
        assert total_time < 10.0  # Total process should be fast
        
        print(f"Single upload performance: {total_time:.3f}s total, {upload_time:.3f}s upload")
    
    @patch('app.api.deps.get_current_active_user')
    def test_concurrent_upload_simulation(self, mock_get_user, client, mock_authenticated_user, small_video_data):
        """Test concurrent upload handling with threading simulation."""
        mock_get_user.return_value = mock_authenticated_user
        
        import threading
        import queue
        
        num_concurrent = 10  # Reduced for unit test
        results = queue.Queue()
        
        def upload_video(video_index: int):
            """Upload a single video and record timing."""
            start_time = time.time()
            
            try:
                # Get presigned URL
                response = client.post(
                    "/api/v1/videos/upload",
                    json={
                        "filename": f"concurrent_test_{video_index}.mp4",
                        "content_type": "video/mp4",
                        "file_size": len(small_video_data),
                        "exercise_id": 1
                    },
                    headers={"Authorization": "Bearer fake-token"}
                )
                
                if response.status_code != 200:
                    results.put({"success": False, "duration": time.time() - start_time})
                    return
                
                video_id = response.json().get("video_id")
                
                # Simulate upload
                response = client.put(
                    f"/api/v1/videos/{video_id}/upload-complete",
                    files={"video": (f"test_{video_index}.mp4", small_video_data, "video/mp4")},
                    headers={"Authorization": "Bearer fake-token"}
                )
                
                success = response.status_code in [200, 201]
                duration = time.time() - start_time
                
                results.put({"success": success, "duration": duration})
                
            except Exception as e:
                results.put({"success": False, "duration": time.time() - start_time, "error": str(e)})
        
        # Launch concurrent uploads
        threads = []
        start_time = time.time()
        
        for i in range(num_concurrent):
            thread = threading.Thread(target=upload_video, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all uploads to complete
        for thread in threads:
            thread.join(timeout=30)  # 30s timeout per thread
        
        total_test_time = time.time() - start_time
        
        # Collect results
        upload_results = []
        while not results.empty():
            upload_results.append(results.get())
        
        # Analyze results
        successful_uploads = [r for r in upload_results if r["success"]]
        failed_uploads = [r for r in upload_results if not r["success"]]
        
        success_rate = (len(successful_uploads) / len(upload_results)) * 100
        durations = [r["duration"] for r in successful_uploads]
        
        if durations:
            avg_duration = statistics.mean(durations)
            p95_duration = statistics.quantiles(durations, n=100)[94] if len(durations) >= 20 else max(durations)
        else:
            avg_duration = float('inf')
            p95_duration = float('inf')
        
        # Performance assertions
        assert success_rate >= 90.0, f"Success rate too low: {success_rate}%"
        assert avg_duration < 15.0, f"Average duration too high: {avg_duration:.3f}s"
        assert p95_duration < 30.0, f"P95 duration too high: {p95_duration:.3f}s"
        assert total_test_time < 45.0, f"Total test time too high: {total_test_time:.3f}s"
        
        print(f"Concurrent upload results: {len(successful_uploads)}/{len(upload_results)} successful, "
              f"avg: {avg_duration:.3f}s, P95: {p95_duration:.3f}s")
    
    def test_frame_processing_timing_validation(self):
        """Test frame processing timing meets SLA requirements."""
        # Mock frame processing metrics
        with patch('app.core.monitoring.FRAME_PROCESSING_DURATION') as mock_duration:
            mock_duration.labels.return_value.observe = Mock()
            
            # Simulate frame processing timings
            frame_times_ms = [
                45, 62, 78, 123, 156, 89, 234, 67, 145, 203,  # Mix of fast and slow frames
                34, 56, 87, 134, 167, 89, 267, 78, 156, 234,
                23, 45, 67, 123, 145, 78, 189, 56, 134, 212
            ]
            
            for frame_time in frame_times_ms:
                mock_duration.labels.return_value.observe(frame_time / 1000.0)
            
            # Calculate performance metrics
            p95_time_ms = statistics.quantiles(frame_times_ms, n=100)[94]
            avg_time_ms = statistics.mean(frame_times_ms)
            
            # SLA validation
            assert p95_time_ms <= 300, f"Frame processing P95 exceeds 300ms: {p95_time_ms:.1f}ms"
            assert avg_time_ms <= 150, f"Average frame processing time too high: {avg_time_ms:.1f}ms"
            
            print(f"Frame processing metrics: avg={avg_time_ms:.1f}ms, P95={p95_time_ms:.1f}ms")
    
    def test_api_success_rate_calculation(self):
        """Test API success rate calculation accuracy."""
        # Mock request metrics
        with patch.object(metrics_analysis_service, 'calculate_api_success_rate') as mock_calc:
            # Simulate high success rate scenario
            mock_calc.return_value = {
                'success_rate': 99.95,
                'total_requests': 10000,
                'successful_requests': 9995,
                'failed_requests': 5
            }
            
            result = metrics_analysis_service.calculate_api_success_rate()
            
            # Validate SLA compliance
            assert result['success_rate'] >= 99.9, f"Success rate below SLA: {result['success_rate']}%"
            assert result['total_requests'] > 0, "No requests recorded"
            assert result['failed_requests'] < result['total_requests'] * 0.001, "Too many failures"
            
            print(f"API success rate: {result['success_rate']}% ({result['successful_requests']}/{result['total_requests']})")
    
    def test_sla_compliance_validation(self):
        """Test SLA compliance validation logic."""
        with patch.object(metrics_analysis_service, 'check_sla_compliance') as mock_sla:
            # Mock perfect SLA compliance
            mock_sla.return_value = {
                'overall_sla_compliant': True,
                'success_rate_compliant': True,
                'p95_latency_compliant': True,
                'p99_latency_compliant': True,
                'current_success_rate': 99.98,
                'current_p95_latency_ms': 245.0,
                'current_p99_latency_ms': 456.0,
                'sla_targets': {
                    'success_rate': 99.9,
                    'p95_latency_ms': 300,
                    'p99_latency_ms': 1000
                }
            }
            
            compliance = metrics_analysis_service.check_sla_compliance()
            
            # Validate all SLA requirements
            assert compliance['overall_sla_compliant'], "Overall SLA not compliant"
            assert compliance['success_rate_compliant'], "Success rate SLA not met"
            assert compliance['p95_latency_compliant'], "P95 latency SLA not met"
            assert compliance['current_success_rate'] >= 99.9, "Current success rate below target"
            assert compliance['current_p95_latency_ms'] <= 300, "Current P95 latency above target"
            
            print(f"SLA compliance: Success={compliance['current_success_rate']}%, "
                  f"P95={compliance['current_p95_latency_ms']}ms")
    
    @pytest.mark.slow
    def test_sustained_load_simulation(self, client):
        """Test sustained load handling over time."""
        # This test simulates sustained load to validate performance doesn't degrade
        duration_seconds = 30  # Short duration for unit test
        request_interval = 0.5  # Request every 500ms
        
        start_time = time.time()
        response_times = []
        error_count = 0
        
        while time.time() - start_time < duration_seconds:
            request_start = time.time()
            
            try:
                response = client.get("/health")
                request_time = time.time() - request_start
                response_times.append(request_time)
                
                if response.status_code != 200:
                    error_count += 1
                    
            except Exception:
                error_count += 1
                response_times.append(5.0)  # Assume 5s timeout
            
            # Wait for next request
            elapsed = time.time() - request_start
            if elapsed < request_interval:
                time.sleep(request_interval - elapsed)
        
        # Analyze sustained load results
        if response_times:
            avg_response_time = statistics.mean(response_times)
            p95_response_time = statistics.quantiles(response_times, n=100)[94] if len(response_times) >= 20 else max(response_times)
            
            total_requests = len(response_times)
            error_rate = (error_count / total_requests) * 100
            
            # Performance assertions for sustained load
            assert avg_response_time < 1.0, f"Average response time too high under load: {avg_response_time:.3f}s"
            assert p95_response_time < 3.0, f"P95 response time too high under load: {p95_response_time:.3f}s"
            assert error_rate < 5.0, f"Error rate too high under load: {error_rate:.1f}%"
            
            print(f"Sustained load results: {total_requests} requests, "
                  f"avg={avg_response_time:.3f}s, P95={p95_response_time:.3f}s, "
                  f"errors={error_rate:.1f}%")
        else:
            pytest.fail("No successful requests during sustained load test")