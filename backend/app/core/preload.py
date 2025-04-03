"""
Preload module for caching frequently accessed data.

This module contains functions to preload data into Redis cache
during application startup, to improve performance for common queries.
"""
import asyncio
from app.core.logging import get_logger
from app.core.cache import cache_service
from app.db.session import SessionLocal
from app.models.exercise import Exercise
from app.models.form_check import FormCheck
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import json

logger = get_logger(__name__)

async def preload_caches():
    """Preload frequently accessed data into cache."""
    if not cache_service.available:
        logger.warning("Cache service not available, skipping preload")
        return
    
    tasks = [
        preload_exercises(),
        preload_form_check_stats(),
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Check for exceptions
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Error in preload task {i}: {str(result)}")
    
    logger.info("Cache preloading completed")

async def preload_exercises():
    """Preload exercise data into cache."""
    logger.info("Preloading exercises data")
    
    try:
        # Create a new session for this operation
        db = SessionLocal()
        
        # Get all exercises with efficient loading
        result = await db.execute(
            select(Exercise)
            .options(selectinload(Exercise.form_checks))
        )
        exercises = result.scalars().all()
        
        # Cache the exercise list
        exercise_list = [{
            "id": ex.id,
            "name": ex.name,
            "exercise_type": ex.exercise_type,
            "description": ex.description,
            "form_check_count": len(ex.form_checks) if ex.form_checks else 0
        } for ex in exercises]
        
        await cache_service.set("exercises:all", json.dumps(exercise_list), expire=3600)  # 1 hour
        
        # Cache individual exercises
        for ex in exercises:
            await cache_service.set(
                f"exercise:{ex.id}", 
                json.dumps({
                    "id": ex.id,
                    "name": ex.name,
                    "exercise_type": ex.exercise_type,
                    "description": ex.description,
                    "form_check_count": len(ex.form_checks) if ex.form_checks else 0,
                    "created_at": ex.created_at.isoformat() if ex.created_at else None,
                    "updated_at": ex.updated_at.isoformat() if ex.updated_at else None
                }),
                expire=3600  # 1 hour
            )
        
        logger.info(f"Preloaded {len(exercises)} exercises to cache")
        
    except Exception as e:
        logger.error(f"Error preloading exercises: {str(e)}")
        raise
    finally:
        await db.close()

async def preload_form_check_stats():
    """Preload form check statistics for dashboard."""
    logger.info("Preloading form check statistics")
    
    try:
        # Create a new session for this operation
        db = SessionLocal()
        
        # Get form check counts by status
        result = await db.execute("""
            SELECT status, COUNT(*) as count 
            FROM form_checks 
            GROUP BY status
        """)
        status_counts = {row[0]: row[1] for row in result}
        
        # Get form check counts by exercise type
        result = await db.execute("""
            SELECT exercise_type, COUNT(*) as count 
            FROM form_checks 
            GROUP BY exercise_type
        """)
        exercise_type_counts = {row[0]: row[1] for row in result}
        
        # Get average scores
        result = await db.execute("""
            SELECT AVG(overall_score) as avg_score
            FROM form_checks
            WHERE overall_score IS NOT NULL
        """)
        avg_score = result.scalar() or 0
        
        # Combine stats
        stats = {
            "status_counts": status_counts,
            "exercise_type_counts": exercise_type_counts,
            "avg_score": float(avg_score),
            "total_form_checks": sum(status_counts.values()),
            "updated_at": datetime.now().isoformat()
        }
        
        await cache_service.set("stats:form_checks", json.dumps(stats), expire=3600)  # 1 hour
        logger.info("Preloaded form check statistics to cache")
        
    except Exception as e:
        logger.error(f"Error preloading form check stats: {str(e)}")
        raise
    finally:
        await db.close()

async def preload_recent_feedback():
    """Preload recent feedback examples for quick reference."""
    logger.info("Preloading recent feedback examples")
    
    try:
        # Create a new session for this operation
        db = SessionLocal()
        
        # Get recent feedback with high scores as examples
        result = await db.execute("""
            SELECT fc.id, fc.exercise_type, fc.overall_score, fc.summary
            FROM form_checks fc
            WHERE fc.overall_score > 7
            ORDER BY fc.created_at DESC
            LIMIT 20
        """)
        
        good_examples = [{
            "id": row[0],
            "exercise_type": row[1],
            "overall_score": row[2],
            "summary": row[3]
        } for row in result]
        
        # Get recent feedback with low scores as examples
        result = await db.execute("""
            SELECT fc.id, fc.exercise_type, fc.overall_score, fc.summary
            FROM form_checks fc
            WHERE fc.overall_score < 4
            ORDER BY fc.created_at DESC
            LIMIT 20
        """)
        
        improvement_examples = [{
            "id": row[0],
            "exercise_type": row[1],
            "overall_score": row[2],
            "summary": row[3]
        } for row in result]
        
        await cache_service.set(
            "feedback:good_examples", 
            json.dumps(good_examples), 
            expire=86400  # 24 hours
        )
        
        await cache_service.set(
            "feedback:improvement_examples", 
            json.dumps(improvement_examples), 
            expire=86400  # 24 hours
        )
        
        logger.info("Preloaded feedback examples to cache")
        
    except Exception as e:
        logger.error(f"Error preloading feedback examples: {str(e)}")
    finally:
        await db.close() 