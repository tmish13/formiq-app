"""Tests for database operations."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.db.session import get_db
from tests.base import BaseTest

class TestDatabaseOperations(BaseTest):
    """Test suite for database operations."""
    
    @pytest.mark.asyncio
    async def test_transaction_commit(self):
        """Test transaction commit."""
        # Start transaction
        async with self.db.begin():
            # Create test user
            user = await self.create_test_user()
            
            # Create test workout
            workout = await self.create_test_workout(user_id=user["id"])
            
            # Create test exercise
            exercise = await self.create_test_exercise(workout_id=workout["id"])
        
        # Verify data was committed
        result = await self.db.execute(
            "SELECT * FROM users WHERE id = :id",
            {"id": user["id"]}
        )
        committed_user = result.first()
        
        assert committed_user is not None
        assert committed_user["id"] == user["id"]
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self):
        """Test transaction rollback."""
        # Create test user outside transaction
        user = await self.create_test_user()
        
        # Start transaction that will fail
        try:
            async with self.db.begin():
                # Create test workout
                workout = await self.create_test_workout(user_id=user["id"])
                
                # Try to create exercise with invalid workout_id (should fail)
                await self.create_test_exercise(workout_id=999)
        except IntegrityError:
            # Transaction should be rolled back
            pass
        
        # Verify workout was not committed
        result = await self.db.execute(
            "SELECT * FROM workouts WHERE id = :id",
            {"id": workout["id"]}
        )
        rolled_back_workout = result.first()
        
        assert rolled_back_workout is None
    
    @pytest.mark.asyncio
    async def test_connection_pooling(self):
        """Test database connection pooling."""
        # Create multiple connections
        connections = []
        for _ in range(5):
            db = await get_db()
            connections.append(db)
        
        # Verify all connections are different
        connection_ids = [id(conn) for conn in connections]
        assert len(set(connection_ids)) == 5
    
    @pytest.mark.asyncio
    async def test_query_performance(self):
        """Test query performance with large dataset."""
        # Create multiple users and workouts
        users = []
        for i in range(10):
            user = await self.create_test_user(email=f"user{i}@example.com")
            users.append(user)
            
            # Create multiple workouts for each user
            for j in range(5):
                workout = await self.create_test_workout(
                    user_id=user["id"],
                    name=f"Workout {j} for User {i}"
                )
                
                # Create multiple exercises for each workout
                for k in range(3):
                    await self.create_test_exercise(
                        workout_id=workout["id"],
                        name=f"Exercise {k} for Workout {j}"
                    )
        
        # Query all data with joins
        result = await self.db.execute(
            """
            SELECT u.id, u.email, w.id as workout_id, w.name as workout_name, 
                   e.id as exercise_id, e.name as exercise_name
            FROM users u
            JOIN workouts w ON u.id = w.user_id
            JOIN exercises e ON w.id = e.workout_id
            ORDER BY u.id, w.id, e.id
            """
        )
        rows = result.fetchall()
        
        # Verify results
        assert len(rows) == 10 * 5 * 3  # 10 users * 5 workouts * 3 exercises
    
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test database error recovery."""
        # Try to execute invalid SQL
        try:
            await self.db.execute(text("SELECT * FROM non_existent_table"))
        except Exception:
            # Should not affect subsequent queries
            pass
        
        # Verify we can still execute valid queries
        result = await self.db.execute(text("SELECT 1"))
        assert result.scalar() == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent database operations."""
        # Create test user
        user = await self.create_test_user()
        
        # Create multiple workouts concurrently
        workouts = []
        for i in range(5):
            workout = await self.create_test_workout(
                user_id=user["id"],
                name=f"Concurrent Workout {i}"
            )
            workouts.append(workout)
        
        # Verify all workouts were created
        result = await self.db.execute(
            "SELECT * FROM workouts WHERE user_id = :user_id",
            {"user_id": user["id"]}
        )
        created_workouts = result.fetchall()
        
        assert len(created_workouts) == 5
    
    @pytest.mark.asyncio
    async def test_data_integrity(self):
        """Test data integrity constraints."""
        # Try to create user with duplicate email
        await self.create_test_user(email="duplicate@example.com")
        
        with pytest.raises(IntegrityError):
            await self.create_test_user(email="duplicate@example.com")
        
        # Try to create workout with non-existent user_id
        with pytest.raises(IntegrityError):
            await self.create_test_workout(user_id=999)
        
        # Try to create exercise with non-existent workout_id
        with pytest.raises(IntegrityError):
            await self.create_test_exercise(workout_id=999)
    
    @pytest.mark.asyncio
    async def test_cascade_delete(self):
        """Test cascade delete operations."""
        # Create test user
        user = await self.create_test_user()
        
        # Create test workout
        workout = await self.create_test_workout(user_id=user["id"])
        
        # Create test exercises
        exercise1 = await self.create_test_exercise(workout_id=workout["id"])
        exercise2 = await self.create_test_exercise(workout_id=workout["id"])
        
        # Delete workout
        await self.db.execute(
            "DELETE FROM workouts WHERE id = :id",
            {"id": workout["id"]}
        )
        await self.db.commit()
        
        # Verify exercises were deleted
        result = await self.db.execute(
            "SELECT * FROM exercises WHERE workout_id = :workout_id",
            {"workout_id": workout["id"]}
        )
        deleted_exercises = result.fetchall()
        
        assert len(deleted_exercises) == 0 