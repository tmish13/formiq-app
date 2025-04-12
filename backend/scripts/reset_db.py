"""Script to reset and initialize the database."""
import asyncio
import os
import sys
import datetime
import subprocess
from pathlib import Path
import asyncpg
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
import redis.asyncio

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings


async def clear_redis_cache() -> None:
    """Clear all Redis cache data."""
    try:
        if settings.USE_REDIS_CACHE:
            redis = await redis.asyncio.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB
            )
            await redis.flushdb()
            await redis.close()
            print("Redis cache cleared successfully.")
    except Exception as e:
        print(f"Warning: Could not clear Redis cache: {e}")


async def backup_database() -> bool:
    """Create a backup of the database before reset."""
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Path("database_backups")
        backup_dir.mkdir(exist_ok=True)
        backup_file = backup_dir / f"backup_{timestamp}.sql"

        # Use subprocess.run for better security and error handling
        result = subprocess.run([
            'pg_dump',
            '-h', settings.POSTGRES_SERVER,
            '-p', str(settings.POSTGRES_PORT),
            '-U', settings.POSTGRES_USER,
            '-d', settings.POSTGRES_DB,
            '-f', str(backup_file)
        ], env={
            'PGPASSWORD': settings.POSTGRES_PASSWORD,
            **os.environ
        }, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Warning: Backup failed: {result.stderr}")
            return False

        print(f"Database backup created at: {backup_file}")
        return True
    except Exception as e:
        print(f"Warning: Could not create database backup: {e}")
        return False


async def initialize_seed_data(engine) -> None:
    """Initialize seed data for the database."""
    try:
        async with engine.connect() as conn:
            # Start transaction
            await conn.execute(text("BEGIN"))
            
            try:
                # 1. Insert exercise categories first
                await conn.execute(text("""
                    INSERT INTO exercise_categories (name, description, created_at, updated_at)
                    VALUES 
                        ('strength', 'Strength training exercises', NOW(), NOW()),
                        ('cardio', 'Cardiovascular exercises', NOW(), NOW()),
                        ('flexibility', 'Flexibility and mobility exercises', NOW(), NOW()),
                        ('core', 'Core strengthening exercises', NOW(), NOW()),
                        ('balance', 'Balance and stability exercises', NOW(), NOW())
                    ON CONFLICT (name) DO NOTHING;
                """))

                # 2. Insert default exercise types with categories
                await conn.execute(text("""
                    INSERT INTO exercises (name, description, difficulty_level, category_id, created_at, updated_at)
                    SELECT 
                        e.name, 
                        e.description, 
                        e.difficulty_level,
                        ec.id,
                        NOW(),
                        NOW()
                    FROM (
                        VALUES 
                            ('Push-up', 'Basic upper body exercise', 'beginner', 'strength'),
                            ('Squat', 'Basic lower body exercise', 'beginner', 'strength'),
                            ('Plank', 'Core stability exercise', 'beginner', 'core'),
                            ('Jumping Jack', 'Full body cardio exercise', 'beginner', 'cardio'),
                            ('Forward Bend', 'Standing forward bend stretch', 'beginner', 'flexibility'),
                            ('Single-Leg Stand', 'Basic balance exercise', 'beginner', 'balance')
                    ) as e(name, description, difficulty_level, category)
                    JOIN exercise_categories ec ON ec.name = e.category
                    ON CONFLICT (name) DO NOTHING;
                """))
                
                # 3. Insert default workout plans
                await conn.execute(text("""
                    INSERT INTO workout_plans (name, description, difficulty_level, created_at, updated_at)
                    VALUES 
                        ('Beginner Strength', 'Basic strength training program', 'beginner', NOW(), NOW()),
                        ('Core Fundamentals', 'Basic core workout program', 'beginner', NOW(), NOW()),
                        ('Cardio Starter', 'Introduction to cardio exercises', 'beginner', NOW(), NOW()),
                        ('Flexibility Basics', 'Basic flexibility routine', 'beginner', NOW(), NOW())
                    ON CONFLICT (name) DO NOTHING;
                """))

                # 4. Create default admin user
                from app.core.security import get_password_hash
                admin_password = settings.FIRST_SUPERUSER_PASSWORD
                hashed_password = get_password_hash(admin_password)
                
                await conn.execute(text("""
                    INSERT INTO users (
                        email,
                        hashed_password,
                        full_name,
                        is_superuser,
                        is_active,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        :email,
                        :hashed_password,
                        'System Administrator',
                        TRUE,
                        TRUE,
                        NOW(),
                        NOW()
                    )
                    ON CONFLICT (email) DO NOTHING;
                """), {
                    "email": settings.FIRST_SUPERUSER,
                    "hashed_password": hashed_password
                })
                
                # Commit transaction if all operations succeed
                await conn.execute(text("COMMIT"))
                print("Seed data initialized successfully.")
                print(f"Admin user created with email: {settings.FIRST_SUPERUSER}")
            
            except Exception as e:
                # Rollback transaction if any operation fails
                await conn.execute(text("ROLLBACK"))
                raise e
                
    except Exception as e:
        print(f"Warning: Could not initialize seed data: {e}")


async def check_postgres_connection() -> bool:
    """Check if we can connect to PostgreSQL server."""
    try:
        conn = await asyncpg.connect(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database='postgres',
            host=settings.POSTGRES_SERVER,
            port=settings.POSTGRES_PORT
        )
        await conn.close()
        return True
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return False


async def reset_database() -> None:
    """Reset the database by dropping and recreating it."""
    try:
        # First check if we can connect to PostgreSQL
        if not await check_postgres_connection():
            print("Cannot connect to PostgreSQL server. Please check your database settings and ensure PostgreSQL is running.")
            sys.exit(1)

        # Create backup before reset
        if not await backup_database():
            print("Backup creation failed. Aborting database reset.")
            sys.exit(1)

        # Clear Redis cache
        await clear_redis_cache()

        # Connect to default postgres database to manage our app database
        conn = await asyncpg.connect(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database='postgres',
            host=settings.POSTGRES_SERVER,
            port=settings.POSTGRES_PORT
        )

        # Drop connections to our database
        await conn.execute(f'''
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{settings.POSTGRES_DB}'
            AND pid <> pg_backend_pid();
        ''')

        # Drop and recreate database
        await conn.execute(f'DROP DATABASE IF EXISTS {settings.POSTGRES_DB}')
        await conn.execute(f'CREATE DATABASE {settings.POSTGRES_DB}')
        await conn.close()

        print(f"Database '{settings.POSTGRES_DB}' has been reset.")

    except Exception as e:
        print(f"Error resetting database: {e}")
        sys.exit(1)


def run_migrations() -> None:
    """Run all alembic migrations."""
    try:
        # Get the alembic.ini file path
        alembic_ini = str(Path(__file__).parent.parent / 'alembic.ini')
        
        if not os.path.exists(alembic_ini):
            print(f"Error: alembic.ini not found at {alembic_ini}")
            sys.exit(1)
        
        # Create Alembic configuration object
        alembic_cfg = Config(alembic_ini)
        
        # Run the migrations
        command.upgrade(alembic_cfg, "head")
        
        print("Database migrations completed successfully.")

    except Exception as e:
        print(f"Error running migrations: {e}")
        sys.exit(1)


async def verify_database() -> None:
    """Verify that the database was initialized correctly."""
    try:
        # Create async engine
        engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
        
        # Check if all tables exist
        expected_tables = {
            'users',
            'subscriptions',
            'exercises',
            'workouts',
            'workout_exercises',
            'workout_plans',
            'workout_plan_workouts',
            'form_checks',
            'exercise_categories',  # Added missing table
            'alembic_version'
        }
        
        async with engine.connect() as conn:
            # Check tables
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            existing_tables = {row[0] for row in result}
            
            # Check indexes
            result = await conn.execute(text("""
                SELECT tablename, indexname 
                FROM pg_indexes 
                WHERE schemaname = 'public'
            """))
            existing_indexes = {row[1] for row in result}

            # Verify foreign key constraints
            result = await conn.execute(text("""
                SELECT
                    tc.table_name, kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM
                    information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage AS ccu
                      ON ccu.constraint_name = tc.constraint_name
                WHERE constraint_type = 'FOREIGN KEY';
            """))
            foreign_keys = list(result)
        
        missing_tables = expected_tables - existing_tables
        if missing_tables:
            print(f"Error: Missing tables: {missing_tables}")
            sys.exit(1)
        
        # Verify essential indexes exist
        essential_indexes = {
            'ix_users_email',
            'ix_users_is_active',
            'ix_form_checks_user_id',
            'ix_workouts_user_id',
            'ix_exercise_categories_name'  # Added missing index
        }
        missing_indexes = essential_indexes - existing_indexes
        if missing_indexes:
            print(f"Warning: Missing some important indexes: {missing_indexes}")
        
        # Verify foreign key relationships
        required_relationships = {
            ('exercises', 'category_id', 'exercise_categories', 'id'),
            ('workout_exercises', 'exercise_id', 'exercises', 'id'),
            ('workout_exercises', 'workout_id', 'workouts', 'id')
        }
        existing_relationships = {(fk[0], fk[1], fk[2], fk[3]) for fk in foreign_keys}
        missing_relationships = required_relationships - existing_relationships
        if missing_relationships:
            print(f"Warning: Missing foreign key relationships: {missing_relationships}")
        
        print("Database verification completed successfully.")
        print(f"All expected tables are present: {', '.join(sorted(expected_tables))}")

        # Initialize seed data
        await initialize_seed_data(engine)

    except Exception as e:
        print(f"Error verifying database: {e}")
        sys.exit(1)


async def main() -> None:
    """Main function to reset and initialize the database."""
    print("Starting database reset and initialization...")
    print(f"Using database: {settings.POSTGRES_DB} on server: {settings.POSTGRES_SERVER}")
    
    await reset_database()
    run_migrations()
    await verify_database()
    
    print("Database reset and initialization completed successfully.")


if __name__ == "__main__":
    asyncio.run(main()) 