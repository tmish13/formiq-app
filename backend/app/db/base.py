"""Database base module."""
from app.db.base_class import Base

# Import all models here so that Base has them before being imported by Alembic
from app.models.user import User
from app.models.exercise import ExerciseTemplate
from app.models.form_check import FormCheck, FeedbackItem
from app.models.workout import Workout, Exercise, WorkoutPlan 