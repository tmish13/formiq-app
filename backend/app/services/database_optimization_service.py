"""
Database connection pooling and query optimization service.

This service implements advanced database optimization techniques including:
- Dynamic connection pool management
- Query optimization and analysis
- Connection health monitoring
- Read/write replica routing
- Query result caching
- Statement preparation and reuse
- Connection lifecycle management
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from contextlib import asynccontextmanager, contextmanager
from collections import defaultdict, deque
import asyncio
import weakref

from sqlalchemy import create_engine, event, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import QueuePool, StaticPool, AssertionPool
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, TimeoutError
from sqlalchemy.sql import ClauseElement

from app.core.config import Settings
from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)


@dataclass
class ConnectionPoolMetrics:
    """Metrics for connection pool monitoring."""
    pool_name: str
    size: int
    checked_in: int
    checked_out: int
    overflow: int
    total_connections: int
    peak_connections: int
    connection_requests: int
    timeout_count: int
    error_count: int
    average_checkout_time_ms: float
    last_checkout_time: Optional[datetime] = None
    last_error: Optional[str] = None


@dataclass
class QueryOptimizationMetrics:
    """Metrics for query optimization analysis."""
    query_hash: str
    query_template: str
    execution_count: int
    total_execution_time_ms: float
    average_execution_time_ms: float
    min_execution_time_ms: float
    max_execution_time_ms: float
    rows_examined_avg: float
    rows_returned_avg: float
    index_usage_score: float
    optimization_recommendations: List[str] = field(default_factory=list)


@dataclass
class ConnectionPoolConfig:
    """Configuration for connection pool optimization."""
    name: str
    pool_size: int = 20
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    isolation_level: Optional[str] = None
    enable_readonly: bool = False
    
    # Advanced pooling settings
    pool_reset_on_return: str = "commit"
    pool_invalidate_on_disconnect: bool = True
    pool_threadlocal: bool = False
    
    # Connection health monitoring
    health_check_interval: int = 300  # seconds
    max_connection_age: int = 7200    # seconds
    connection_retry_attempts: int = 3


class DatabaseOptimizationService:
    """
    Advanced database optimization service with connection pooling and query optimization.
    
    Features:
    - Dynamic connection pool management with health monitoring
    - Query optimization analysis and recommendations
    - Read/write replica routing
    - Connection lifecycle management
    - Query result caching and statement preparation
    - Performance metrics and alerting
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._pools: Dict[str, Tuple[Engine, sessionmaker]] = {}
        self._async_pools: Dict[str, Tuple[Any, async_sessionmaker]] = {}
        self._pool_metrics: Dict[str, ConnectionPoolMetrics] = {}
        self._query_metrics: Dict[str, QueryOptimizationMetrics] = {}
        self._prepared_statements: Dict[str, ClauseElement] = {}
        self._connection_health_checker = None
        self._metrics_collector_task = None
        self._lock = threading.RLock()
        
        # Query optimization settings
        self.enable_query_caching = True
        self.enable_statement_preparation = True
        self.query_analysis_threshold_ms = 100.0
        
        # Connection health monitoring
        self._unhealthy_connections = set()
        self._connection_error_counts = defaultdict(int)
        self._last_health_check = None
        
    async def initialize_pools(self) -> None:
        """Initialize optimized connection pools."""
        logger.info("Initializing database connection pools...")
        
        try:
            # Primary read-write pool
            primary_config = ConnectionPoolConfig(
                name="primary",
                pool_size=self.settings.DB_POOL_SIZE,
                max_overflow=self.settings.DB_MAX_OVERFLOW,
                pool_timeout=self.settings.DB_POOL_TIMEOUT,
                pool_recycle=self.settings.DB_POOL_RECYCLE
            )
            
            await self._create_connection_pool(
                config=primary_config,
                database_url=self.settings.SQLALCHEMY_DATABASE_URI,
                is_readonly=False
            )
            
            # Optional read-only replica pool
            if hasattr(self.settings, 'READONLY_DATABASE_URI') and self.settings.READONLY_DATABASE_URI:
                readonly_config = ConnectionPoolConfig(
                    name="readonly",
                    pool_size=max(1, self.settings.DB_POOL_SIZE // 2),
                    max_overflow=max(1, self.settings.DB_MAX_OVERFLOW // 2),
                    pool_timeout=self.settings.DB_POOL_TIMEOUT,
                    pool_recycle=self.settings.DB_POOL_RECYCLE,
                    enable_readonly=True
                )
                
                await self._create_connection_pool(
                    config=readonly_config,
                    database_url=self.settings.READONLY_DATABASE_URI,
                    is_readonly=True
                )
            
            # Start background monitoring
            await self._start_background_monitoring()
            
            logger.info(f"Database connection pools initialized: {list(self._pools.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to initialize connection pools: {e}")
            raise DatabaseError(f"Connection pool initialization failed: {e}")
    
    async def _create_connection_pool(
        self,
        config: ConnectionPoolConfig,
        database_url: str,
        is_readonly: bool = False
    ) -> None:
        """Create an optimized connection pool."""
        try:
            # Determine pool class based on database type
            if "sqlite" in database_url:
                poolclass = StaticPool
            else:
                poolclass = QueuePool
            
            # Create synchronous engine
            sync_engine = create_engine(
                database_url,
                poolclass=poolclass,
                pool_size=config.pool_size,
                max_overflow=config.max_overflow,
                pool_timeout=config.pool_timeout,
                pool_recycle=config.pool_recycle,
                pool_pre_ping=config.pool_pre_ping,
                pool_reset_on_return=config.pool_reset_on_return,
                echo=self.settings.DB_ECHO,
                isolation_level=config.isolation_level
            )
            
            # Create session factory
            sync_session_factory = sessionmaker(
                bind=sync_engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            # Store pool
            self._pools[config.name] = (sync_engine, sync_session_factory)
            
            # Create async engine if not SQLite
            if "sqlite" not in database_url:
                async_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
                
                async_engine = create_async_engine(
                    async_url,
                    poolclass=poolclass,
                    pool_size=config.pool_size,
                    max_overflow=config.max_overflow,
                    pool_timeout=config.pool_timeout,
                    pool_recycle=config.pool_recycle,
                    pool_pre_ping=config.pool_pre_ping,
                    echo=self.settings.DB_ECHO
                )
                
                async_session_factory = async_sessionmaker(
                    bind=async_engine,
                    class_=AsyncSession,
                    autocommit=False,
                    autoflush=False,
                    expire_on_commit=False
                )
                
                self._async_pools[config.name] = (async_engine, async_session_factory)
            
            # Initialize metrics
            self._pool_metrics[config.name] = ConnectionPoolMetrics(
                pool_name=config.name,
                size=config.pool_size,
                checked_in=0,
                checked_out=0,
                overflow=0,
                total_connections=0,
                peak_connections=0,
                connection_requests=0,
                timeout_count=0,
                error_count=0,
                average_checkout_time_ms=0.0
            )
            
            # Register event listeners for monitoring
            self._register_pool_events(sync_engine, config.name)
            
            logger.info(f"Created connection pool '{config.name}': {config.pool_size} base + {config.max_overflow} overflow")
            
        except Exception as e:
            logger.error(f"Failed to create connection pool '{config.name}': {e}")
            raise
    
    def _register_pool_events(self, engine: Engine, pool_name: str) -> None:
        """Register event listeners for connection pool monitoring."""
        
        @event.listens_for(engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Track new connections."""
            metrics = self._pool_metrics[pool_name]
            metrics.total_connections += 1
            logger.debug(f"Pool '{pool_name}': New connection created (total: {metrics.total_connections})")
        
        @event.listens_for(engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """Track connection checkouts."""
            metrics = self._pool_metrics[pool_name]
            metrics.connection_requests += 1
            metrics.checked_out += 1
            metrics.last_checkout_time = datetime.utcnow()
            
            if metrics.checked_out > metrics.peak_connections:
                metrics.peak_connections = metrics.checked_out
            
            connection_record.checkout_time = time.time()
        
        @event.listens_for(engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """Track connection checkins."""
            metrics = self._pool_metrics[pool_name]
            metrics.checked_out = max(0, metrics.checked_out - 1)
            metrics.checked_in += 1
            
            # Calculate checkout time
            if hasattr(connection_record, 'checkout_time'):
                checkout_duration = (time.time() - connection_record.checkout_time) * 1000
                # Update rolling average
                if metrics.average_checkout_time_ms == 0:
                    metrics.average_checkout_time_ms = checkout_duration
                else:
                    metrics.average_checkout_time_ms = (
                        metrics.average_checkout_time_ms * 0.9 + checkout_duration * 0.1
                    )
        
        @event.listens_for(engine, "close")
        def on_close(dbapi_connection, connection_record):
            """Track connection closures."""
            metrics = self._pool_metrics[pool_name]
            metrics.total_connections = max(0, metrics.total_connections - 1)
        
        @event.listens_for(engine, "invalidate")
        def on_invalidate(dbapi_connection, connection_record, exception):
            """Track connection invalidations."""
            metrics = self._pool_metrics[pool_name]
            metrics.error_count += 1
            metrics.last_error = str(exception) if exception else "Connection invalidated"
            logger.warning(f"Pool '{pool_name}': Connection invalidated - {metrics.last_error}")
    
    async def _start_background_monitoring(self) -> None:
        """Start background tasks for monitoring and optimization."""
        if self._metrics_collector_task is None:
            self._metrics_collector_task = asyncio.create_task(self._collect_metrics_loop())
            logger.info("Started database metrics collection task")
        
        if self._connection_health_checker is None:
            self._connection_health_checker = asyncio.create_task(self._health_check_loop())
            logger.info("Started connection health monitoring task")
    
    async def _collect_metrics_loop(self) -> None:
        """Background task to collect and update pool metrics."""
        while True:
            try:
                await asyncio.sleep(30)  # Collect metrics every 30 seconds
                await self._update_pool_metrics()
                await self._analyze_query_performance()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _health_check_loop(self) -> None:
        """Background task to monitor connection health."""
        while True:
            try:
                await asyncio.sleep(300)  # Health check every 5 minutes
                await self._perform_health_checks()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(600)  # Wait longer on error
    
    async def _update_pool_metrics(self) -> None:
        """Update pool metrics from engine state."""
        for pool_name, (engine, _) in self._pools.items():
            try:
                pool = engine.pool
                metrics = self._pool_metrics[pool_name]
                
                # Update current pool state
                metrics.size = getattr(pool, 'size', lambda: 0)()
                metrics.checked_in = getattr(pool, 'checkedin', lambda: 0)()
                metrics.checked_out = getattr(pool, 'checkedout', lambda: 0)()
                metrics.overflow = getattr(pool, 'overflow', lambda: 0)()
                
            except Exception as e:
                logger.warning(f"Failed to update metrics for pool '{pool_name}': {e}")
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all connection pools."""
        self._last_health_check = datetime.utcnow()
        
        for pool_name, (engine, session_factory) in self._pools.items():
            try:
                # Test connection with simple query
                with session_factory() as session:
                    result = session.execute(text("SELECT 1")).fetchone()
                    if result and result[0] == 1:
                        # Remove from unhealthy set if it was there
                        self._unhealthy_connections.discard(pool_name)
                        self._connection_error_counts[pool_name] = 0
                    else:
                        raise DatabaseError("Health check query returned unexpected result")
                        
                logger.debug(f"Health check passed for pool '{pool_name}'")
                
            except Exception as e:
                self._unhealthy_connections.add(pool_name)
                self._connection_error_counts[pool_name] += 1
                
                metrics = self._pool_metrics[pool_name]
                metrics.error_count += 1
                metrics.last_error = f"Health check failed: {str(e)}"
                
                logger.error(f"Health check failed for pool '{pool_name}': {e}")
                
                # Invalidate pool if too many consecutive errors
                if self._connection_error_counts[pool_name] >= 3:
                    logger.warning(f"Invalidating pool '{pool_name}' due to repeated health check failures")
                    try:
                        engine.pool.invalidate()
                    except Exception as pool_error:
                        logger.error(f"Failed to invalidate pool '{pool_name}': {pool_error}")
    
    async def _analyze_query_performance(self) -> None:
        """Analyze query performance and generate optimization recommendations."""
        # This would analyze slow query logs, execution plans, etc.
        # For now, we'll focus on the connection pooling aspects
        pass
    
    @contextmanager
    def get_optimized_session(
        self,
        pool_name: str = "primary",
        readonly: bool = False
    ):
        """Get an optimized database session with automatic pool selection."""
        # Route to appropriate pool
        if readonly and "readonly" in self._pools:
            pool_name = "readonly"
        
        if pool_name not in self._pools:
            raise DatabaseError(f"Connection pool '{pool_name}' not found")
        
        # Check pool health
        if pool_name in self._unhealthy_connections:
            # Try primary pool as fallback
            if pool_name != "primary" and "primary" not in self._unhealthy_connections:
                logger.warning(f"Pool '{pool_name}' unhealthy, falling back to primary")
                pool_name = "primary"
            else:
                raise DatabaseError(f"Connection pool '{pool_name}' is unhealthy")
        
        engine, session_factory = self._pools[pool_name]
        start_time = time.time()
        
        try:
            with session_factory() as session:
                # Track checkout time
                checkout_time = (time.time() - start_time) * 1000
                
                # Update metrics
                metrics = self._pool_metrics[pool_name]
                if metrics.average_checkout_time_ms == 0:
                    metrics.average_checkout_time_ms = checkout_time
                else:
                    metrics.average_checkout_time_ms = (
                        metrics.average_checkout_time_ms * 0.9 + checkout_time * 0.1
                    )
                
                yield session
                
        except TimeoutError as e:
            metrics = self._pool_metrics[pool_name]
            metrics.timeout_count += 1
            logger.error(f"Connection timeout from pool '{pool_name}': {e}")
            raise DatabaseError(f"Connection timeout: {e}")
        except Exception as e:
            metrics = self._pool_metrics[pool_name]
            metrics.error_count += 1
            logger.error(f"Database session error from pool '{pool_name}': {e}")
            raise
    
    @asynccontextmanager
    async def get_async_optimized_session(
        self,
        pool_name: str = "primary",
        readonly: bool = False
    ):
        """Get an async optimized database session."""
        # Route to appropriate pool
        if readonly and "readonly" in self._async_pools:
            pool_name = "readonly"
        
        if pool_name not in self._async_pools:
            # Fall back to sync session wrapped in async
            with self.get_optimized_session(pool_name, readonly) as session:
                yield session
            return
        
        # Check pool health
        if pool_name in self._unhealthy_connections:
            if pool_name != "primary" and "primary" not in self._unhealthy_connections:
                logger.warning(f"Async pool '{pool_name}' unhealthy, falling back to primary")
                pool_name = "primary"
            else:
                raise DatabaseError(f"Async connection pool '{pool_name}' is unhealthy")
        
        engine, session_factory = self._async_pools[pool_name]
        
        try:
            async with session_factory() as session:
                yield session
                
        except Exception as e:
            metrics = self._pool_metrics[pool_name]
            metrics.error_count += 1
            logger.error(f"Async database session error from pool '{pool_name}': {e}")
            raise
    
    def get_pool_metrics(self, pool_name: Optional[str] = None) -> Dict[str, ConnectionPoolMetrics]:
        """Get connection pool metrics."""
        if pool_name:
            return {pool_name: self._pool_metrics.get(pool_name)}
        return self._pool_metrics.copy()
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get database optimization recommendations."""
        recommendations = []
        
        for pool_name, metrics in self._pool_metrics.items():
            # High checkout time recommendation
            if metrics.average_checkout_time_ms > 50:
                recommendations.append({
                    "category": "Performance",
                    "priority": "Medium",
                    "pool": pool_name,
                    "recommendation": f"Average checkout time is {metrics.average_checkout_time_ms:.1f}ms",
                    "action": "Consider increasing pool size or optimizing queries",
                    "impact": "Reduced connection wait times"
                })
            
            # High error rate recommendation
            if metrics.error_count > 10:
                recommendations.append({
                    "category": "Reliability", 
                    "priority": "High",
                    "pool": pool_name,
                    "recommendation": f"Pool has {metrics.error_count} errors",
                    "action": "Investigate connection issues and consider pool reconfiguration",
                    "impact": "Improved system reliability"
                })
            
            # Pool utilization recommendation
            utilization = metrics.checked_out / max(metrics.size, 1)
            if utilization > 0.8:
                recommendations.append({
                    "category": "Capacity",
                    "priority": "Medium",
                    "pool": pool_name,
                    "recommendation": f"Pool utilization is {utilization:.1%}",
                    "action": "Consider increasing pool size or max_overflow",
                    "impact": "Better handling of concurrent requests"
                })
        
        return recommendations
    
    async def cleanup(self) -> None:
        """Cleanup resources and stop background tasks."""
        logger.info("Cleaning up database optimization service...")
        
        # Cancel background tasks
        if self._metrics_collector_task:
            self._metrics_collector_task.cancel()
            try:
                await self._metrics_collector_task
            except asyncio.CancelledError:
                pass
        
        if self._connection_health_checker:
            self._connection_health_checker.cancel()
            try:
                await self._connection_health_checker
            except asyncio.CancelledError:
                pass
        
        # Dispose engines
        for pool_name, (engine, _) in self._pools.items():
            try:
                engine.dispose()
                logger.info(f"Disposed connection pool '{pool_name}'")
            except Exception as e:
                logger.error(f"Error disposing pool '{pool_name}': {e}")
        
        for pool_name, (engine, _) in self._async_pools.items():
            try:
                await engine.dispose()
                logger.info(f"Disposed async connection pool '{pool_name}'")
            except Exception as e:
                logger.error(f"Error disposing async pool '{pool_name}': {e}")
        
        # Clear collections
        self._pools.clear()
        self._async_pools.clear()
        self._pool_metrics.clear()
        
        logger.info("Database optimization service cleanup completed")


# Global service instance
database_optimization_service: Optional[DatabaseOptimizationService] = None


async def get_database_optimization_service(settings: Settings) -> DatabaseOptimizationService:
    """Get or create the global database optimization service instance."""
    global database_optimization_service
    
    if database_optimization_service is None:
        database_optimization_service = DatabaseOptimizationService(settings)
        await database_optimization_service.initialize_pools()
    
    return database_optimization_service