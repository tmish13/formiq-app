"""Tests for metrics analysis service."""

import pytest
from unittest.mock import Mock, patch

from app.services.metrics_analysis_service import MetricsAnalysisService


class TestMetricsAnalysisService:
    """Test suite for metrics analysis service."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.service = MetricsAnalysisService()
    
    def test_init(self):
        """Test service initialization."""
        assert self.service.success_rate_sla == 99.9
        assert self.service.p95_latency_sla_ms == 300
        assert self.service.p99_latency_sla_ms == 1000
    
    @patch('app.services.metrics_analysis_service.REGISTRY')
    def test_calculate_api_success_rate_no_metric(self, mock_registry):
        """Test success rate calculation when no metric is available."""
        mock_registry._collector_to_names = {}
        
        result = self.service.calculate_api_success_rate()
        
        expected = {
            'success_rate': 0.0, 
            'total_requests': 0, 
            'successful_requests': 0
        }
        assert result == expected
    
    @patch('app.services.metrics_analysis_service.REGISTRY')
    def test_calculate_api_success_rate_with_data(self, mock_registry):
        """Test success rate calculation with mock metric data."""
        # Mock metric collector
        mock_collector = Mock()
        mock_collector._name = 'http_requests_total'
        
        # Mock samples with different status codes
        mock_sample_200 = Mock()
        mock_sample_200.value = 950  # 950 successful requests
        mock_sample_200.labels = {'status': '200', 'endpoint': '/api/v1/health'}
        
        mock_sample_404 = Mock()
        mock_sample_404.value = 30   # 30 not found requests
        mock_sample_404.labels = {'status': '404', 'endpoint': '/api/v1/missing'}
        
        mock_sample_500 = Mock()
        mock_sample_500.value = 20   # 20 server errors
        mock_sample_500.labels = {'status': '500', 'endpoint': '/api/v1/error'}
        
        mock_family = Mock()
        mock_family.samples = [mock_sample_200, mock_sample_404, mock_sample_500]
        
        mock_collector.collect.return_value = [mock_family]
        
        # Configure registry mock
        mock_registry._collector_to_names = {mock_collector: ['http_requests_total']}
        
        result = self.service.calculate_api_success_rate()
        
        # Total: 950 + 30 + 20 = 1000
        # Successful: 950 (only 2xx responses)
        # Success rate: 950/1000 * 100 = 95%
        assert result['success_rate'] == 95.0
        assert result['total_requests'] == 1000
        assert result['successful_requests'] == 950
        assert result['failed_requests'] == 50
    
    @patch('app.services.metrics_analysis_service.REGISTRY')  
    def test_calculate_api_success_rate_with_3xx(self, mock_registry):
        """Test that 3xx responses are counted as successful."""
        mock_collector = Mock()
        mock_collector._name = 'http_requests_total'
        
        # Mock samples with 2xx and 3xx responses
        mock_sample_200 = Mock()
        mock_sample_200.value = 800
        mock_sample_200.labels = {'status': '200'}
        
        mock_sample_301 = Mock()
        mock_sample_301.value = 150  # Redirects should be successful
        mock_sample_301.labels = {'status': '301'}
        
        mock_sample_500 = Mock()
        mock_sample_500.value = 50
        mock_sample_500.labels = {'status': '500'}
        
        mock_family = Mock()
        mock_family.samples = [mock_sample_200, mock_sample_301, mock_sample_500]
        mock_collector.collect.return_value = [mock_family]
        
        mock_registry._collector_to_names = {mock_collector: ['http_requests_total']}
        
        result = self.service.calculate_api_success_rate()
        
        # Total: 1000, Successful: 950 (200 + 301), Success rate: 95%
        assert result['success_rate'] == 95.0
        assert result['successful_requests'] == 950
    
    @patch('app.services.metrics_analysis_service.REGISTRY')
    def test_calculate_latency_percentiles_no_metric(self, mock_registry):
        """Test latency calculation when no metric is available."""
        mock_registry._collector_to_names = {}
        
        result = self.service.calculate_latency_percentiles()
        
        assert result == {'p50': 0.0, 'p95': 0.0, 'p99': 0.0}
    
    def test_check_sla_compliance_good_metrics(self):
        """Test SLA compliance check with good metrics."""
        with patch.object(self.service, 'calculate_api_success_rate') as mock_success:
            with patch.object(self.service, 'calculate_latency_percentiles') as mock_latency:
                # Mock good metrics
                mock_success.return_value = {'success_rate': 99.95}
                mock_latency.return_value = {'p95': 150.0, 'p99': 250.0}
                
                result = self.service.check_sla_compliance()
                
                assert result['overall_sla_compliant'] is True
                assert result['success_rate_compliant'] is True
                assert result['p95_latency_compliant'] is True
                assert result['p99_latency_compliant'] is True
                assert result['current_success_rate'] == 99.95
    
    def test_check_sla_compliance_poor_metrics(self):
        """Test SLA compliance check with poor metrics."""
        with patch.object(self.service, 'calculate_api_success_rate') as mock_success:
            with patch.object(self.service, 'calculate_latency_percentiles') as mock_latency:
                # Mock poor metrics
                mock_success.return_value = {'success_rate': 98.5}  # Below 99.9%
                mock_latency.return_value = {'p95': 450.0, 'p99': 1200.0}  # Above thresholds
                
                result = self.service.check_sla_compliance()
                
                assert result['overall_sla_compliant'] is False
                assert result['success_rate_compliant'] is False
                assert result['p95_latency_compliant'] is False
                assert result['p99_latency_compliant'] is False
    
    @patch('app.services.metrics_analysis_service.REGISTRY')
    def test_get_endpoint_success_rates(self, mock_registry):
        """Test per-endpoint success rate calculation."""
        mock_collector = Mock()
        mock_collector._name = 'http_requests_total'
        
        # Mock samples for different endpoints
        samples = [
            Mock(value=100, labels={'status': '200', 'endpoint': '/api/v1/health'}),
            Mock(value=5, labels={'status': '500', 'endpoint': '/api/v1/health'}),
            Mock(value=200, labels={'status': '200', 'endpoint': '/api/v1/users'}),
            Mock(value=0, labels={'status': '500', 'endpoint': '/api/v1/users'}),
        ]
        
        mock_family = Mock()
        mock_family.samples = samples
        mock_collector.collect.return_value = [mock_family]
        
        mock_registry._collector_to_names = {mock_collector: ['http_requests_total']}
        
        result = self.service.get_endpoint_success_rates()
        
        # Health endpoint: 100/105 = 95.24%
        assert abs(result['/api/v1/health']['success_rate'] - 95.238) < 0.001
        assert result['/api/v1/health']['total_requests'] == 105
        assert result['/api/v1/health']['successful_requests'] == 100
        
        # Users endpoint: 200/200 = 100%
        assert result['/api/v1/users']['success_rate'] == 100.0
        assert result['/api/v1/users']['total_requests'] == 200
    
    def test_generate_prometheus_queries(self):
        """Test Prometheus query generation."""
        queries = self.service.generate_prometheus_queries()
        
        assert 'success_rate_5m' in queries
        assert 'error_rate_5m' in queries
        assert 'p95_latency_5m' in queries
        assert 'sla_compliance_success_rate' in queries
        
        # Check that queries contain expected elements
        success_query = queries['success_rate_5m']
        assert 'status=~"2.."' in success_query
        assert 'rate(' in success_query
        assert '* 100' in success_query
        
        # Check SLA compliance query includes threshold
        sla_query = queries['sla_compliance_success_rate']
        assert '99.9' in sla_query
    
    def test_error_handling_in_success_rate_calculation(self):
        """Test error handling in success rate calculation."""
        with patch('app.services.metrics_analysis_service.REGISTRY') as mock_registry:
            # Make registry access raise an exception
            mock_registry._collector_to_names.__iter__.side_effect = Exception("Registry error")
            
            result = self.service.calculate_api_success_rate()
            
            # Should return default values on error
            assert result['success_rate'] == 0.0
            assert result['total_requests'] == 0
            assert result['successful_requests'] == 0
    
    def test_error_handling_in_sla_compliance(self):
        """Test error handling in SLA compliance check."""
        with patch.object(self.service, 'calculate_api_success_rate') as mock_success:
            # Make success rate calculation raise an exception
            mock_success.side_effect = Exception("Calculation error")
            
            result = self.service.check_sla_compliance()
            
            # Should return error indicator
            assert result['overall_sla_compliant'] is False
            assert 'error' in result