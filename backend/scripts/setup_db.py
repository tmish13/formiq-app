"""
Setup script for initializing the database for testing.

This script will:
1. Drop all existing tables (if any)
2. Create the database structure based on defined models
3. Create a test user
4. Create an exercise template
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

# Load test environment
load_dotenv(".env.test")

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import models
from app.db.base_class import Base
from app.models.user import User
from app.models.subscription import Subscription
from app.models.form_check import FormCheck, FeedbackItem
from app.models.workout import Workout, Exercise, WorkoutPlan
from app.models.exercise import ExerciseTemplate
from app.models.enums import (
    SubscriptionTier,
    FormCheckStatus,
    FeedbackType,
    FeedbackSeverity,
    ExerciseType
)

# Create database engine
engine = create_engine("sqlite:///./test.db")
Session = sessionmaker(bind=engine)

def reset_database():
    """Drop all tables and recreate them."""
    print("Dropping existing tables...")
    Base.metadata.drop_all(bind=engine)
    
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    print("Database structure created successfully.")

def create_test_user():
    """Create a test user for development purposes."""
    session = Session()
    
    try:
        # Check if test user already exists
        existing_user = session.query(User).filter_by(email="test@example.com").first()
        if existing_user:
            print(f"Test user already exists with ID: {existing_user.id}")
            return existing_user.id
            
        # Create test user
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            username="test_user",
            password="Test@123",  # This will be hashed by the model
            is_active=True,
            is_email_verified=True,
            is_verified=True,
            subscription_tier=SubscriptionTier.FREE
        )
        
        session.add(user)
        session.commit()
        
        user_id = user.id
        print(f"Test user created with ID: {user_id}")
        return user_id
        
    except Exception as e:
        session.rollback()
        print(f"Error creating test user: {str(e)}")
        return None
    finally:
        session.close()

def create_exercise_template():
    """Create exercise templates for testing."""
    session = Session()
    
    try:
        # Check if exercise template already exists
        existing_template = session.query(ExerciseTemplate).filter_by(name="Squat").first()
        if existing_template:
            print(f"Exercise template 'Squat' already exists with ID: {existing_template.id}")
            return existing_template.id
            
        # Create exercise template
        template = ExerciseTemplate(
            id=uuid.uuid4(),
            name="Squat",
            description="A compound, full body exercise that trains primarily the muscles of the thighs, hips, buttocks, quadriceps, and hamstrings.",
            difficulty="Beginner",
            muscle_group="Legs",
            equipment="Bodyweight"
        )
        
        session.add(template)
        session.commit()
        
        template_id = template.id
        print(f"Exercise template 'Squat' created with ID: {template_id}")
        return template_id
        
    except Exception as e:
        session.rollback()
        print(f"Error creating exercise template: {str(e)}")
        return None
    finally:
        session.close()

if __name__ == "__main__":
    reset_database()
    user_id = create_test_user()
    template_id = create_exercise_template()
    
    if user_id and template_id:
        print("Database setup completed successfully.")
    else:
        print("Database setup completed with errors.") 