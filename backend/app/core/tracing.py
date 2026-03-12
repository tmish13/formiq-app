"""OpenTelemetry tracing configuration with enhanced error handling."""
import logging
from typing import Any, Optional, Dict
import os

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global tracing state
_tracer_provider: Optional[Any] = None
_tracer: Optional[Any] = None
_is_initialized: bool = False


def _safe_import(module_name: str) -> Optional[Any]:
    """Safely import a module and return None if import fails."""
    try:
        import importlib
        return importlib.import_module(module_name)
    except ImportError as e:
        logger.debug(f"Could not import {module_name}: {e}")
        return None


def setup_tracing() -> bool:
    """
    Configure OpenTelemetry tracing with comprehensive error handling.
    
    Returns:
        bool: True if tracing was successfully configured, False otherwise
    """
    global _tracer_provider, _tracer, _is_initialized
    
    # Check if tracing is enabled
    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry tracing disabled via configuration")
        return False
    
    # Check if already initialized
    if _is_initialized:
        logger.debug("OpenTelemetry already initialized")
        return True
    
    # Import OpenTelemetry modules
    trace_module = _safe_import('opentelemetry.trace')
    trace_provider_module = _safe_import('opentelemetry.sdk.trace')
    trace_export = _safe_import('opentelemetry.sdk.trace.export')
    resource_module = _safe_import('opentelemetry.sdk.resources')
    
    if not all([trace_module, trace_provider_module, trace_export, resource_module]):
        logger.warning("Core OpenTelemetry modules not available. Tracing disabled.")
        return False
    
    try:
        # Create resource with service information
        resource = resource_module.Resource(
            attributes={
                resource_module.SERVICE_NAME: settings.OTEL_SERVICE_NAME,
                resource_module.SERVICE_VERSION: "1.0.0",
                "environment": settings.ENVIRONMENT
            }
        )
        
        # Initialize tracer provider with sampling
        sampler = None
        if hasattr(trace_provider_module, 'TraceIdRatioBasedSampler'):
            sampler = trace_provider_module.TraceIdRatioBasedSampler(settings.TRACE_SAMPLE_RATE)
        
        provider = trace_provider_module.TracerProvider(
            resource=resource,
            sampler=sampler
        )
        
        # Configure exporters
        exporters = []
        
        # OTLP Exporter (preferred)
        if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
            otlp_module = _safe_import('opentelemetry.exporter.otlp.proto.grpc.trace_exporter')
            if otlp_module:
                try:
                    exporter = otlp_module.OTLPSpanExporter(
                        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT
                    )
                    exporters.append(exporter)
                    logger.info(f"OTLP exporter configured: {settings.OTEL_EXPORTER_OTLP_ENDPOINT}")
                except Exception as e:
                    logger.warning(f"Failed to configure OTLP exporter: {e}")
        
        # Jaeger Exporter (fallback)
        if not exporters:
            jaeger_module = _safe_import('opentelemetry.exporter.jaeger.thrift')
            if jaeger_module:
                try:
                    exporter = jaeger_module.JaegerExporter(
                        agent_host_name=settings.JAEGER_HOST,
                        agent_port=settings.JAEGER_PORT,
                    )
                    exporters.append(exporter)
                    logger.info(f"Jaeger exporter configured: {settings.JAEGER_HOST}:{settings.JAEGER_PORT}")
                except Exception as e:
                    logger.warning(f"Failed to configure Jaeger exporter: {e}")
        
        # Add span processors for each exporter
        for exporter in exporters:
            span_processor = trace_export.BatchSpanProcessor(exporter)
            provider.add_span_processor(span_processor)
        
        # Set global tracer provider
        trace_module.set_tracer_provider(provider)
        
        # Store references
        _tracer_provider = provider
        _tracer = trace_module.get_tracer(__name__)
        
        # Setup automatic instrumentation
        _setup_instrumentation()
        
        _is_initialized = True
        logger.info(f"OpenTelemetry tracing configured successfully with {len(exporters)} exporter(s)")
        return True
        
    except Exception as e:
        logger.error(f"Failed to configure OpenTelemetry tracing: {e}")
        return False


def _setup_instrumentation() -> None:
    """Set up automatic instrumentation for common libraries."""
    instrumentations = [
        ('opentelemetry.instrumentation.fastapi', 'FastAPIInstrumentor'),
        ('opentelemetry.instrumentation.sqlalchemy', 'SQLAlchemyInstrumentor'),
        ('opentelemetry.instrumentation.redis', 'RedisInstrumentor'),
        ('opentelemetry.instrumentation.httpx', 'HTTPXClientInstrumentor'),
        ('opentelemetry.instrumentation.requests', 'RequestsInstrumentor'),
        ('opentelemetry.instrumentation.logging', 'LoggingInstrumentor'),
    ]
    
    for module_name, instrumentor_name in instrumentations:
        module = _safe_import(module_name)
        if module and hasattr(module, instrumentor_name):
            try:
                instrumentor_class = getattr(module, instrumentor_name)
                instrumentor = instrumentor_class()
                
                # Check if already instrumented
                if not hasattr(instrumentor, '_is_instrumented') or not instrumentor._is_instrumented:
                    instrumentor.instrument()
                    logger.debug(f"Successfully instrumented {instrumentor_name}")
                    
            except Exception as e:
                logger.warning(f"Failed to instrument {instrumentor_name}: {e}")


def get_tracer(name: str = __name__) -> Any:
    """
    Get a tracer instance.
    
    Args:
        name: Name of the tracer
        
    Returns:
        Tracer instance if available, otherwise a no-op tracer
    """
    if _tracer:
        return _tracer
    
    # Return a no-op tracer if tracing is not available
    trace_module = _safe_import('opentelemetry.trace')
    if trace_module:
        return trace_module.get_tracer(name)
    
    # Fallback to no-op tracer
    return NoOpTracer()


def get_current_span() -> Any:
    """Get the current active span."""
    trace_module = _safe_import('opentelemetry.trace')
    if trace_module:
        return trace_module.get_current_span()
    return None


def get_trace_context() -> Dict[str, str]:
    """Get current trace context information for logging."""
    context = {}
    
    if not settings.TRACE_CORRELATION_ENABLED:
        return context
    
    try:
        span = get_current_span()
        if span and hasattr(span, 'get_span_context'):
            span_context = span.get_span_context()
            if hasattr(span_context, 'trace_id') and hasattr(span_context, 'span_id'):
                # Convert to hex strings for logging
                trace_id = f"{span_context.trace_id:032x}"
                span_id = f"{span_context.span_id:016x}"
                
                context.update({
                    'trace_id': trace_id,
                    'span_id': span_id,
                    'correlation_id': trace_id[:16]  # Shorter correlation ID
                })
    except Exception as e:
        logger.debug(f"Failed to extract trace context: {e}")
    
    return context


def is_tracing_enabled() -> bool:
    """Check if tracing is properly configured and enabled."""
    return _is_initialized and _tracer_provider is not None


class NoOpTracer:
    """No-operation tracer for when OpenTelemetry is not available."""
    
    def start_span(self, name: str, **kwargs) -> 'NoOpSpan':
        return NoOpSpan()
    
    def start_as_current_span(self, name: str, **kwargs):
        return NoOpSpan()


class NoOpSpan:
    """No-operation span for when OpenTelemetry is not available."""
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def set_attribute(self, key: str, value: Any) -> None:
        pass
    
    def set_status(self, status: Any) -> None:
        pass
    
    def record_exception(self, exception: Exception) -> None:
        pass
    
    def end(self) -> None:
        pass