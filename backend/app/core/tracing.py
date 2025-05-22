"""OpenTelemetry tracing configuration."""
from typing import Any, Optional, Protocol, runtime_checkable
from types import ModuleType

# Core imports that should always be available
from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import ConfigurationException

# Type definitions for static type checking
@runtime_checkable
class Tracer(Protocol):
    def start_span(self, name: str, **kwargs: Any) -> Any: ...
    def get_current_span(self) -> Any: ...

class TracerProvider(Protocol):
    def get_tracer(self, name: str, **kwargs: Any) -> Tracer: ...

# Global state with proper type hints
_tracer_provider: Optional[Any] = None
_trace_module: Optional[ModuleType] = None

logger = get_logger(__name__)

def _import_module(module_path: str) -> Optional[ModuleType]:
    """Safely import a module and return None if import fails."""
    try:
        module_parts = module_path.split('.')
        if len(module_parts) == 1:
            return __import__(module_path)
        
        return __import__(module_path, fromlist=[module_parts[-1]])
    except ImportError as e:
        logger.debug(f"Could not import {module_path}: {str(e)}")
        return None

def setup_tracing() -> None:
    """Configure OpenTelemetry tracing with proper error handling."""
    global _tracer_provider, _trace_module

    # Import core OpenTelemetry modules
    trace_module = _import_module('opentelemetry.trace')
    trace_provider = _import_module('opentelemetry.sdk.trace')
    batch_processor = _import_module('opentelemetry.sdk.trace.export')
    jaeger = _import_module('opentelemetry.exporter.jaeger.thrift')

    if not all([trace_module, trace_provider, batch_processor, jaeger]):
        logger.warning("Core OpenTelemetry modules not available. Tracing disabled.")
        return

    try:
        # Initialize tracer provider
        provider = trace_provider.TracerProvider()  # type: ignore
        trace_module.set_tracer_provider(provider)  # type: ignore
        
        # Configure Jaeger exporter
        jaeger_exporter = jaeger.JaegerExporter(  # type: ignore
            agent_host_name=settings.JAEGER_HOST,
            agent_port=settings.JAEGER_PORT,
            service_name=settings.PROJECT_NAME,
        )
        
        # Set up batch processor
        span_processor = batch_processor.BatchSpanProcessor(jaeger_exporter)  # type: ignore
        provider.add_span_processor(span_processor)
        
        # Store globals
        _tracer_provider = provider
        _trace_module = trace_module
        
        # Set up instrumentations
        _setup_instrumentation('fastapi')
        _setup_instrumentation('sqlalchemy')
        _setup_instrumentation('redis')
        _setup_instrumentation('httpx')
        
        logger.info("Tracing configured successfully")
        
    except Exception as e:
        logger.error(f"Failed to configure tracing: {str(e)}")
        raise ConfigurationException(f"Failed to configure tracing: {str(e)}")

def _setup_instrumentation(name: str) -> None:
    """Set up a specific instrumentation by name."""
    module = _import_module(f'opentelemetry.instrumentation.{name}')
    if module is None:
        logger.warning(f"{name.title()} instrumentation not available")
        return

    try:
        if name == 'fastapi':
            module.FastAPIInstrumentor.instrument()  # type: ignore
        elif name == 'sqlalchemy':
            module.SQLAlchemyInstrumentor().instrument()  # type: ignore
        elif name == 'redis':
            module.RedisInstrumentor().instrument()  # type: ignore
        elif name == 'httpx':
            module.HTTPXClientInstrumentor().instrument()  # type: ignore
        
        logger.info(f"{name.title()} instrumentation successful")
    except Exception as e:
        logger.warning(f"Failed to set up {name} instrumentation: {str(e)}")

def get_tracer(name: str) -> Optional[Tracer]:
    """
    Get a tracer instance with proper type checking.
    
    Args:
        name: Name of the tracer
        
    Returns:
        Tracer instance if OpenTelemetry is available, None otherwise
    """
    if _trace_module is None or _tracer_provider is None:
        logger.warning("OpenTelemetry is not available. Returning None for tracer.")
        return None

    try:
        return _trace_module.get_tracer(name)  # type: ignore
    except Exception as e:
        logger.error(f"Failed to get tracer {name}: {str(e)}")
        raise ConfigurationException(f"Failed to get tracer {name}: {str(e)}") 