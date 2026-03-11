"""
Service for analyzing API metrics and calculating success rates.

This service provides utilities for analyzing Prometheus metrics
to calculate API success rates, SLA compliance, and performance indicators.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import statistics

from prometheus_client import REGISTRY
from prometheus_client.samples import Sample

from app.core.config import settings

logger = logging.getLogger(__name__)


class MetricsAnalysisService:
    """Service for analyzing API metrics and performance indicators."""
    
    def __init__(self):
        """Initialize metrics analysis service."""
        self.registry = REGISTRY
        
        # SLA thresholds
        self.success_rate_sla = 99.9  # 99.9% success rate target
        self.p95_latency_sla_ms = 300  # 300ms p95 latency target
        self.p99_latency_sla_ms = 1000  # 1000ms p99 latency target
    
    def calculate_api_success_rate(self, time_window_minutes: int = 5) -> Dict[str, float]:
        """
        Calculate API success rate from Prometheus metrics.
        
        Args:
            time_window_minutes: Time window for calculation
            
        Returns:
            Dictionary with success rate metrics
        """
        try:
            # Get HTTP request counter
            http_requests_metric = None
            for collector in self.registry._collector_to_names:
                if hasattr(collector, '_name') and collector._name == 'http_requests_total':
                    http_requests_metric = collector
                    break
            
            if not http_requests_metric:
                logger.warning("HTTP requests metric not found")
                return {'success_rate': 0.0, 'total_requests': 0, 'successful_requests': 0}
            
            # Collect current values
            total_requests = 0
            successful_requests = 0
            
            for sample in http_requests_metric.collect()[0].samples:
                count = sample.value
                labels = sample.labels
                status = labels.get('status', '000')
                
                total_requests += count
                
                # Consider 2xx and 3xx as successful
                if status.startswith('2') or status.startswith('3'):
                    successful_requests += count
            
            # Calculate success rate
            if total_requests == 0:
                success_rate = 100.0
            else:
                success_rate = (successful_requests / total_requests) * 100
            
            return {
                'success_rate': round(success_rate, 3),
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'failed_requests': total_requests - successful_requests
            }
            
        except Exception as e:
            logger.error(f"Error calculating API success rate: {e}")
            return {'success_rate': 0.0, 'total_requests': 0, 'successful_requests': 0}
    
    def calculate_latency_percentiles(self) -> Dict[str, float]:
        """
        Calculate latency percentiles from HTTP duration histogram.
        
        Returns:
            Dictionary with latency percentiles in milliseconds
        """
        try:
            # Get HTTP duration histogram
            http_duration_metric = None
            for collector in self.registry._collector_to_names:
                if hasattr(collector, '_name') and collector._name == 'http_request_duration_seconds':
                    http_duration_metric = collector
                    break
            
            if not http_duration_metric:
                logger.warning("HTTP duration metric not found")
                return {'p50': 0.0, 'p95': 0.0, 'p99': 0.0}
            
            # Collect histogram data
            total_observations = []
            
            for family in http_duration_metric.collect():
                for sample in family.samples:
                    if sample.name.endswith('_bucket'):
                        # Extract bucket data for percentile calculation
                        le_value = float(sample.labels.get('le', '0'))
                        count = sample.value
                        
                        # Approximate data points for percentile calculation
                        if le_value != float('+Inf'):
                            total_observations.extend([le_value] * int(count))
            
            if not total_observations:
                return {'p50': 0.0, 'p95': 0.0, 'p99': 0.0}
            
            # Calculate percentiles and convert to milliseconds
            total_observations.sort()
            n = len(total_observations)
            
            p50 = statistics.quantiles(total_observations, n=100)[49] * 1000  # 50th percentile
            p95 = statistics.quantiles(total_observations, n=100)[94] * 1000  # 95th percentile
            p99 = statistics.quantiles(total_observations, n=100)[98] * 1000  # 99th percentile
            
            return {
                'p50': round(p50, 2),
                'p95': round(p95, 2),
                'p99': round(p99, 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating latency percentiles: {e}")
            return {'p50': 0.0, 'p95': 0.0, 'p99': 0.0}
    
    def check_sla_compliance(self) -> Dict[str, bool]:
        """
        Check if current metrics meet SLA requirements.
        
        Returns:
            Dictionary with SLA compliance status
        """
        try:
            success_rate_data = self.calculate_api_success_rate()
            latency_data = self.calculate_latency_percentiles()
            
            success_rate_ok = success_rate_data['success_rate'] >= self.success_rate_sla
            p95_latency_ok = latency_data['p95'] <= self.p95_latency_sla_ms
            p99_latency_ok = latency_data['p99'] <= self.p99_latency_sla_ms
            
            overall_sla_ok = success_rate_ok and p95_latency_ok and p99_latency_ok
            
            return {
                'overall_sla_compliant': overall_sla_ok,
                'success_rate_compliant': success_rate_ok,
                'p95_latency_compliant': p95_latency_ok,
                'p99_latency_compliant': p99_latency_ok,
                'current_success_rate': success_rate_data['success_rate'],
                'current_p95_latency_ms': latency_data['p95'],
                'current_p99_latency_ms': latency_data['p99'],
                'sla_targets': {
                    'success_rate': self.success_rate_sla,
                    'p95_latency_ms': self.p95_latency_sla_ms,
                    'p99_latency_ms': self.p99_latency_sla_ms
                }
            }
            
        except Exception as e:
            logger.error(f"Error checking SLA compliance: {e}")
            return {'overall_sla_compliant': False, 'error': str(e)}
    
    def get_endpoint_success_rates(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate success rates per API endpoint.
        
        Returns:
            Dictionary mapping endpoints to their success rate metrics
        """
        try:
            endpoint_stats = {}
            
            # Get HTTP request counter
            http_requests_metric = None
            for collector in self.registry._collector_to_names:
                if hasattr(collector, '_name') and collector._name == 'http_requests_total':
                    http_requests_metric = collector
                    break
            
            if not http_requests_metric:
                return {}
            
            # Collect per-endpoint data
            for sample in http_requests_metric.collect()[0].samples:
                labels = sample.labels
                endpoint = labels.get('endpoint', 'unknown')
                status = labels.get('status', '000')
                count = sample.value
                
                if endpoint not in endpoint_stats:
                    endpoint_stats[endpoint] = {'total': 0, 'successful': 0}
                
                endpoint_stats[endpoint]['total'] += count
                
                if status.startswith('2') or status.startswith('3'):
                    endpoint_stats[endpoint]['successful'] += count
            
            # Calculate success rates
            result = {}
            for endpoint, stats in endpoint_stats.items():
                total = stats['total']
                successful = stats['successful']
                
                if total > 0:
                    success_rate = (successful / total) * 100
                else:
                    success_rate = 100.0
                
                result[endpoint] = {
                    'success_rate': round(success_rate, 3),
                    'total_requests': total,
                    'successful_requests': successful,
                    'failed_requests': total - successful
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating endpoint success rates: {e}")
            return {}
    
    def generate_prometheus_queries(self) -> Dict[str, str]:
        """
        Generate Prometheus queries for success rate monitoring.
        
        Returns:
            Dictionary of useful Prometheus queries
        """
        return {
            'success_rate_5m': 
                'sum(rate(http_requests_total{status=~"2.."}[5m])) / sum(rate(http_requests_total[5m])) * 100',
            
            'success_rate_by_endpoint_5m':
                'sum(rate(http_requests_total{status=~"2.."}[5m])) by (endpoint) / sum(rate(http_requests_total[5m])) by (endpoint) * 100',
            
            'error_rate_5m':
                'sum(rate(http_requests_total{status=~"[45].."}[5m])) / sum(rate(http_requests_total[5m])) * 100',
            
            'p95_latency_5m':
                'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))',
            
            'p99_latency_5m':
                'histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))',
            
            'requests_per_second':
                'sum(rate(http_requests_total[5m]))',
            
            'sla_compliance_success_rate':
                f'(sum(rate(http_requests_total{{status=~"2.."}}[5m])) / sum(rate(http_requests_total[5m])) * 100) >= {self.success_rate_sla}'
        }


# Global instance
metrics_analysis_service = MetricsAnalysisService()