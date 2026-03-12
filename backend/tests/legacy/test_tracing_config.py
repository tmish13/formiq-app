"""Tests for OpenTelemetry tracing configuration."""

import pytest
from unittest.mock import patch, Mock, MagicMock
import logging

from app.core.tracing import (
    setup_tracing,
    get_tracer,
    get_current_span,
    get_trace_context,
    is_tracing_enabled,
    NoOpTracer,
    NoOpSpan
)
from app.core.config import settings


class TestTracingConfiguration:
    """Test suite for OpenTelemetry tracing configuration."""
    
    def setup_method(self):
        """Reset tracing state before each test."""
        # Import the module to reset global state
        import app.core.tracing as tracing_module
        tracing_module._tracer_provider = None
        tracing_module._tracer = None
        tracing_module._is_initialized = False
    
    @patch('app.core.config.settings.OTEL_ENABLED', False)
    def test_setup_tracing_disabled(self):
        """Test tracing setup when OTEL is disabled."""
        result = setup_tracing()
        
        assert result is False
        assert is_tracing_enabled() is False
    
    @patch('app.core.config.settings.OTEL_ENABLED', True)
    @patch('app.core.tracing._safe_import')
    def test_setup_tracing_missing_modules(self, mock_safe_import):
        """Test tracing setup when OpenTelemetry modules are not available."""
        # Mock missing modules
        mock_safe_import.return_value = None
        
        result = setup_tracing()
        
        assert result is False
        assert is_tracing_enabled() is False
    
    @patch('app.core.config.settings.OTEL_ENABLED', True)
    @patch('app.core.config.settings.OTEL_SERVICE_NAME', 'test-service')
    @patch('app.core.config.settings.TRACE_SAMPLE_RATE', 0.5)
    @patch('app.core.config.settings.JAEGER_HOST', 'test-jaeger')
    @patch('app.core.config.settings.JAEGER_PORT', 6831)
    def test_setup_tracing_with_jaeger(self):
        """Test successful tracing setup with Jaeger exporter."""
        # Mock OpenTelemetry modules
        mock_trace = Mock()
        mock_provider_module = Mock()
        mock_export = Mock()
        mock_resource = Mock()
        mock_jaeger = Mock()
        
        # Configure mocks
        mock_resource_instance = Mock()
        mock_resource.Resource.return_value = mock_resource_instance
        
        mock_sampler = Mock()
        mock_provider_module.TraceIdRatioBasedSampler.return_value = mock_sampler
        
        mock_provider_instance = Mock()
        mock_provider_module.TracerProvider.return_value = mock_provider_instance
        
        mock_exporter = Mock()
        mock_jaeger.JaegerExporter.return_value = mock_exporter
        
        mock_processor = Mock()
        mock_export.BatchSpanProcessor.return_value = mock_processor
        
        mock_tracer = Mock()
        mock_trace.get_tracer.return_value = mock_tracer
        
        with patch('app.core.tracing._safe_import') as mock_safe_import:
            # Mock module imports in order
            side_effect_modules = [
                mock_trace,              # opentelemetry.trace
                mock_provider_module,    # opentelemetry.sdk.trace
                mock_export,             # opentelemetry.sdk.trace.export
                mock_resource,           # opentelemetry.sdk.resources
                None,                    # OTLP (not available)
                mock_jaeger,             # Jaeger exporter
                None,                    # FastAPI instrumentation (not available for this test)
                None,                    # SQLAlchemy instrumentation
                None,                    # Redis instrumentation
                None,                    # HTTPX instrumentation
                None,                    # Requests instrumentation
                None,                    # Logging instrumentation
            ]
            mock_safe_import.side_effect = side_effect_modules
            
            result = setup_tracing()
        
        assert result is True
        assert is_tracing_enabled() is True
        
        # Verify resource creation
        mock_resource.Resource.assert_called_once()
        
        # Verify tracer provider creation
        mock_provider_module.TracerProvider.assert_called_once()
        
        # Verify Jaeger exporter configuration
        mock_jaeger.JaegerExporter.assert_called_once_with(
            agent_host_name='test-jaeger',
            agent_port=6831
        )
        
        # Verify span processor addition
        mock_provider_instance.add_span_processor.assert_called_once_with(mock_processor)
        
        # Verify global tracer provider is set
        mock_trace.set_tracer_provider.assert_called_once_with(mock_provider_instance)
    
    @patch('app.core.config.settings.OTEL_ENABLED', True)
    @patch('app.core.config.settings.OTEL_EXPORTER_OTLP_ENDPOINT', 'http://otlp:4317')
    def test_setup_tracing_with_otlp(self):
        """Test successful tracing setup with OTLP exporter."""
        # Mock OpenTelemetry modules
        mock_trace = Mock()
        mock_provider_module = Mock()
        mock_export = Mock()
        mock_resource = Mock()
        mock_otlp = Mock()
        
        # Configure mocks
        mock_resource_instance = Mock()
        mock_resource.Resource.return_value = mock_resource_instance
        
        mock_provider_instance = Mock()
        mock_provider_module.TracerProvider.return_value = mock_provider_instance
        
        mock_exporter = Mock()
        mock_otlp.OTLPSpanExporter.return_value = mock_exporter
        
        mock_processor = Mock()
        mock_export.BatchSpanProcessor.return_value = mock_processor
        
        with patch('app.core.tracing._safe_import') as mock_safe_import:
            side_effect_modules = [
                mock_trace,              # opentelemetry.trace
                mock_provider_module,    # opentelemetry.sdk.trace
                mock_export,             # opentelemetry.sdk.trace.export
                mock_resource,           # opentelemetry.sdk.resources
                mock_otlp,               # OTLP exporter (available)
                # No Jaeger exporter needed since OTLP is available
            ]
            mock_safe_import.side_effect = side_effect_modules
            
            result = setup_tracing()
        
        assert result is True
        
        # Verify OTLP exporter configuration
        mock_otlp.OTLPSpanExporter.assert_called_once_with(
            endpoint='http://otlp:4317'
        )
    
    def test_get_tracer_when_not_initialized(self):
        """Test get_tracer returns NoOpTracer when tracing is not initialized."""
        tracer = get_tracer('test-tracer')
        assert isinstance(tracer, NoOpTracer)
    
    def test_get_current_span_when_not_initialized(self):
        """Test get_current_span returns None when tracing is not initialized."""
        span = get_current_span()
        assert span is None
    
    @patch('app.core.config.settings.TRACE_CORRELATION_ENABLED', False)
    def test_get_trace_context_disabled(self):
        """Test get_trace_context returns empty dict when correlation is disabled."""
        context = get_trace_context()
        assert context == {}
    
    @patch('app.core.config.settings.TRACE_CORRELATION_ENABLED', True)
    def test_get_trace_context_with_span(self):
        """Test get_trace_context extracts trace information from active span."""
        # Mock span and span context
        mock_span_context = Mock()
        mock_span_context.trace_id = 12345678901234567890123456789012  # 32 hex chars
        mock_span_context.span_id = 1234567890123456  # 16 hex chars
        
        mock_span = Mock()
        mock_span.get_span_context.return_value = mock_span_context
        
        with patch('app.core.tracing.get_current_span', return_value=mock_span):
            context = get_trace_context()
        
        assert 'trace_id' in context
        assert 'span_id' in context
        assert 'correlation_id' in context
        assert len(context['correlation_id']) == 16  # First 16 chars of trace_id
    
    def test_no_op_tracer_functionality(self):
        """Test NoOpTracer provides proper no-op behavior."""
        tracer = NoOpTracer()
        
        # Test start_span
        span = tracer.start_span('test-span')
        assert isinstance(span, NoOpSpan)
        
        # Test start_as_current_span
        span2 = tracer.start_as_current_span('test-span-2')
        assert isinstance(span2, NoOpSpan)
    
    def test_no_op_span_functionality(self):
        """Test NoOpSpan provides proper no-op behavior."""
        span = NoOpSpan()
        
        # Test context manager
        with span as ctx_span:
            assert ctx_span is span
        
        # Test methods don't raise exceptions
        span.set_attribute('key', 'value')
        span.set_status('OK')
        span.record_exception(Exception('test'))
        span.end()
        
        # No exceptions should be raised
    
    @patch('app.core.config.settings.OTEL_ENABLED', True)
    def test_setup_tracing_exception_handling(self):
        """Test tracing setup handles exceptions gracefully."""
        with patch('app.core.tracing._safe_import') as mock_safe_import:
            # Mock modules but raise exception during setup
            mock_trace = Mock()
            mock_provider_module = Mock()
            mock_export = Mock()
            mock_resource = Mock()
            
            # Make Resource raise an exception
            mock_resource.Resource.side_effect = Exception("Resource creation failed")
            
            mock_safe_import.side_effect = [
                mock_trace,
                mock_provider_module,
                mock_export,
                mock_resource
            ]
            
            result = setup_tracing()
            
            assert result is False
            assert is_tracing_enabled() is False
    
    def test_setup_tracing_idempotent(self):
        """Test that setup_tracing can be called multiple times safely."""
        with patch('app.core.config.settings.OTEL_ENABLED', True):
            with patch('app.core.tracing._safe_import', return_value=None):
                # First call
                result1 = setup_tracing()
                
                # Second call should not reinitialize
                result2 = setup_tracing()
                
                # Both should return the same result
                assert result1 == result2