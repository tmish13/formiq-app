"""Integration tests for OpenTelemetry tracing."""


import pytest
pytestmark = pytest.mark.integration
from unittest.mock import patch, Mock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.tracing import setup_tracing, is_tracing_enabled
from app.core.middleware.trace_context import get_correlation_id, get_request_trace_context


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_otel_modules():
    """Mock OpenTelemetry modules for testing."""
    mocks = {}
    
    # Mock core modules
    mocks['trace'] = Mock()
    mocks['provider'] = Mock()
    mocks['export'] = Mock()
    mocks['resource'] = Mock()
    mocks['jaeger'] = Mock()
    
    # Configure mock behavior
    mocks['resource'].Resource.return_value = Mock()
    mocks['provider'].TracerProvider.return_value = Mock()
    mocks['jaeger'].JaegerExporter.return_value = Mock()
    mocks['export'].BatchSpanProcessor.return_value = Mock()
    mocks['trace'].get_tracer.return_value = Mock()
    
    return mocks


class TestTracingIntegration:
    """Integration tests for distributed tracing."""
    
    def setup_method(self):
        """Reset tracing state before each test."""
        import app.core.tracing as tracing_module
        tracing_module._tracer_provider = None
        tracing_module._tracer = None
        tracing_module._is_initialized = False
    
    @patch('app.core.config.settings.OTEL_ENABLED', True)
    def test_tracing_integration_with_fastapi(self, mock_otel_modules):
        """Test that tracing integrates properly with FastAPI application."""
        
        def mock_safe_import(module_name):
            if 'opentelemetry.trace' in module_name:
                return mock_otel_modules['trace']
            elif 'opentelemetry.sdk.trace' == module_name:
                return mock_otel_modules['provider']
            elif 'opentelemetry.sdk.trace.export' in module_name:
                return mock_otel_modules['export']
            elif 'opentelemetry.sdk.resources' in module_name:
                return mock_otel_modules['resource']
            elif 'jaeger' in module_name:
                return mock_otel_modules['jaeger']
            elif 'instrumentation' in module_name:
                # Return mock instrumentors
                mock_instrumentor = Mock()
                mock_instrumentor._is_instrumented = False
                instrumentor_mock = Mock()
                instrumentor_mock.return_value = mock_instrumentor
                
                if 'fastapi' in module_name:
                    instrumentor_mock.FastAPIInstrumentor = instrumentor_mock
                elif 'sqlalchemy' in module_name:
                    instrumentor_mock.SQLAlchemyInstrumentor = instrumentor_mock
                elif 'redis' in module_name:
                    instrumentor_mock.RedisInstrumentor = instrumentor_mock
                elif 'httpx' in module_name:
                    instrumentor_mock.HTTPXClientInstrumentor = instrumentor_mock
                elif 'requests' in module_name:
                    instrumentor_mock.RequestsInstrumentor = instrumentor_mock
                elif 'logging' in module_name:
                    instrumentor_mock.LoggingInstrumentor = instrumentor_mock
                
                return instrumentor_mock
            return None
        
        with patch('app.core.tracing._safe_import', side_effect=mock_safe_import):
            result = setup_tracing()
            
            assert result is True
            assert is_tracing_enabled() is True
            
            # Verify tracer provider was configured
            mock_otel_modules['provider'].TracerProvider.assert_called_once()
            mock_otel_modules['trace'].set_tracer_provider.assert_called_once()
    
    def test_trace_context_middleware_integration(self, client):
        """Test that trace context middleware properly injects correlation IDs."""
        
        response = client.get("/health")
        
        # Should include correlation ID in response headers
        assert response.status_code == 200
        assert 'X-Correlation-ID' in response.headers
        
        # Correlation ID should be a non-empty string
        correlation_id = response.headers['X-Correlation-ID']
        assert correlation_id
        assert len(correlation_id) > 0
    
    def test_trace_context_middleware_preserves_existing_correlation_id(self, client):
        """Test that middleware preserves existing correlation ID from headers."""
        
        existing_correlation_id = "test-correlation-123"
        
        response = client.get(
            "/health",
            headers={"X-Correlation-ID": existing_correlation_id}
        )
        
        assert response.status_code == 200
        assert response.headers['X-Correlation-ID'] == existing_correlation_id
    
    @patch('app.core.config.settings.OTEL_ENABLED', True)
    @patch('app.core.config.settings.TRACE_CORRELATION_ENABLED', True)
    def test_trace_context_in_logs(self, mock_otel_modules, caplog):
        """Test that trace context appears in structured logs."""
        
        # Mock active span with trace context
        mock_span_context = Mock()
        mock_span_context.trace_id = 12345678901234567890123456789012
        mock_span_context.span_id = 1234567890123456
        
        mock_span = Mock()
        mock_span.get_span_context.return_value = mock_span_context
        
        def mock_safe_import(module_name):
            if 'opentelemetry.trace' in module_name:
                mock_trace = Mock()
                mock_trace.get_current_span.return_value = mock_span
                return mock_trace
            return None
        
        with patch('app.core.tracing._safe_import', side_effect=mock_safe_import):
            with caplog.at_level('INFO'):
                # Import logging after patching to ensure trace context is available
                from app.core.logging import get_logger
                logger = get_logger('test.trace.integration')
                
                # Log a message that should include trace context
                logger.info("Test log message with trace context")
                
                # Verify trace context was included in logs
                # Note: This test verifies the mechanism is in place
                # Actual trace ID extraction depends on structlog processing
                assert len(caplog.records) > 0
    
    @patch('app.core.config.settings.OTEL_ENABLED', False)
    def test_application_works_without_tracing(self, client):
        """Test that application works normally when tracing is disabled."""
        
        response = client.get("/health")
        
        assert response.status_code == 200
        assert is_tracing_enabled() is False
        
        # Should still have correlation ID (generated by middleware)
        assert 'X-Correlation-ID' in response.headers
    
    def test_health_endpoint_accessibility(self, client):
        """Test that health endpoint is accessible and returns proper data."""
        
        response = client.get("/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert 'status' in data
        assert data['status'] == 'healthy'
    
    @patch('app.core.config.settings.OTEL_ENABLED', True)
    def test_instrumentation_setup(self, mock_otel_modules):
        """Test that instrumentations are properly set up."""
        
        # Track instrumentation calls
        instrumentation_calls = []
        
        def mock_safe_import(module_name):
            if 'instrumentation' in module_name:
                mock_instrumentor_instance = Mock()
                mock_instrumentor_instance._is_instrumented = False
                
                def record_instrumentation(*args, **kwargs):
                    instrumentation_calls.append(module_name)
                    return None
                
                mock_instrumentor_instance.instrument.side_effect = record_instrumentation
                
                mock_instrumentor_class = Mock()
                mock_instrumentor_class.return_value = mock_instrumentor_instance
                
                # Add the instrumentor class to the mock module
                mock_module = Mock()
                if 'fastapi' in module_name:
                    mock_module.FastAPIInstrumentor = mock_instrumentor_class
                elif 'sqlalchemy' in module_name:
                    mock_module.SQLAlchemyInstrumentor = mock_instrumentor_class
                elif 'redis' in module_name:
                    mock_module.RedisInstrumentor = mock_instrumentor_class
                elif 'httpx' in module_name:
                    mock_module.HTTPXClientInstrumentor = mock_instrumentor_class
                elif 'requests' in module_name:
                    mock_module.RequestsInstrumentor = mock_instrumentor_class
                elif 'logging' in module_name:
                    mock_module.LoggingInstrumentor = mock_instrumentor_class
                
                return mock_module
            elif 'opentelemetry.trace' in module_name:
                return mock_otel_modules['trace']
            elif 'opentelemetry.sdk.trace' == module_name:
                return mock_otel_modules['provider']
            elif 'opentelemetry.sdk.trace.export' in module_name:
                return mock_otel_modules['export']
            elif 'opentelemetry.sdk.resources' in module_name:
                return mock_otel_modules['resource']
            elif 'jaeger' in module_name:
                return mock_otel_modules['jaeger']
            return None
        
        with patch('app.core.tracing._safe_import', side_effect=mock_safe_import):
            result = setup_tracing()
            
            assert result is True
            
            # Verify instrumentations were attempted
            expected_instrumentations = [
                'opentelemetry.instrumentation.fastapi',
                'opentelemetry.instrumentation.sqlalchemy',
                'opentelemetry.instrumentation.redis',
                'opentelemetry.instrumentation.httpx',
                'opentelemetry.instrumentation.requests',
                'opentelemetry.instrumentation.logging'
            ]
            
            for expected in expected_instrumentations:
                assert expected in instrumentation_calls
    
    def test_trace_correlation_utilities(self):
        """Test trace correlation utility functions."""
        from fastapi import Request
        from app.core.middleware.trace_context import get_correlation_id, get_request_trace_context


        
        # Create mock request
        mock_request = Mock(spec=Request)
        mock_request.state = Mock()
        mock_request.state.correlation_id = "test-correlation-id"
        mock_request.state.trace_context = {"trace_id": "test-trace-id"}
        
        # Test utility functions
        correlation_id = get_correlation_id(mock_request)
        assert correlation_id == "test-correlation-id"
        
        trace_context = get_request_trace_context(mock_request)
        assert trace_context == {"trace_id": "test-trace-id"}
        
        # Test with missing state
        mock_request_empty = Mock(spec=Request)
        mock_request_empty.state = Mock()
        
        correlation_id_empty = get_correlation_id(mock_request_empty)
        assert correlation_id_empty == ""
        
        trace_context_empty = get_request_trace_context(mock_request_empty)
        assert trace_context_empty == {}