import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models import User, FormCheck
from ..database import get_db, Base, engine
from ..auth import get_password_hash

@pytest.fixture(scope="function")
def db():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Get a test database session
    db = next(get_db())
    
    try:
        yield db
    finally:
        db.close()
        # Drop all tables
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user(db: Session):
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword"),
        subscription_tier="basic",
        subscription_end_date=datetime.now() + timedelta(days=30),
        is_email_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def test_create_user(db: Session):
    user = User(
        email="newuser@example.com",
        username="newuser",
        hashed_password=get_password_hash("newpassword"),
        subscription_tier="free",
        subscription_end_date=datetime.now() + timedelta(days=30),
        is_email_verified=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.id is not None
    assert user.email == "newuser@example.com"
    assert user.username == "newuser"
    assert user.subscription_tier == "free"
    assert user.is_email_verified is False

def test_create_form_check(db: Session, test_user: User):
    form_check = FormCheck(
        user_id=test_user.id,
        exercise_type="squat",
        video_url="https://example.com/video.mp4",
        score=85,
        overall_feedback="Good form overall",
        issues=["Slight knee valgus"]
    )
    db.add(form_check)
    db.commit()
    db.refresh(form_check)

    assert form_check.id is not None
    assert form_check.user_id == test_user.id
    assert form_check.exercise_type == "squat"
    assert form_check.score == 85
    assert form_check.issues == ["Slight knee valgus"]

def test_user_form_checks_relationship(db: Session, test_user: User):
    # Create multiple form checks for the user
    form_checks = [
        FormCheck(
            user_id=test_user.id,
            exercise_type="squat",
            video_url=f"https://example.com/video{i}.mp4",
            score=85 + i,
            overall_feedback=f"Feedback {i}",
            issues=[f"Issue {i}"]
        )
        for i in range(3)
    ]
    
    db.add_all(form_checks)
    db.commit()

    # Refresh the user to get updated relationships
    db.refresh(test_user)

    assert len(test_user.form_checks) == 3
    assert all(fc.user_id == test_user.id for fc in test_user.form_checks)

def test_cascade_delete(db: Session, test_user: User):
    # Create form checks for the user
    form_checks = [
        FormCheck(
            user_id=test_user.id,
            exercise_type="squat",
            video_url=f"https://example.com/video{i}.mp4",
            score=85 + i,
            overall_feedback=f"Feedback {i}",
            issues=[f"Issue {i}"]
        )
        for i in range(3)
    ]
    
    db.add_all(form_checks)
    db.commit()

    # Delete the user
    db.delete(test_user)
    db.commit()

    # Check that form checks were also deleted
    remaining_form_checks = db.query(FormCheck).filter(
        FormCheck.user_id == test_user.id
    ).all()
    assert len(remaining_form_checks) == 0

def test_user_subscription_status(db: Session):
    # Create a user with active subscription
    active_user = User(
        email="active@example.com",
        username="active",
        hashed_password=get_password_hash("password"),
        subscription_tier="pro",
        subscription_end_date=datetime.now() + timedelta(days=30),
        is_email_verified=True
    )
    db.add(active_user)

    # Create a user with expired subscription
    expired_user = User(
        email="expired@example.com",
        username="expired",
        hashed_password=get_password_hash("password"),
        subscription_tier="basic",
        subscription_end_date=datetime.now() - timedelta(days=1),
        is_email_verified=True
    )
    db.add(expired_user)

    db.commit()
    db.refresh(active_user)
    db.refresh(expired_user)

    assert active_user.has_active_subscription() is True
    assert expired_user.has_active_subscription() is False

def test_form_check_validation(db: Session, test_user: User):
    # Test invalid exercise type
    with pytest.raises(ValueError):
        form_check = FormCheck(
            user_id=test_user.id,
            exercise_type="invalid_exercise",
            video_url="https://example.com/video.mp4",
            score=85,
            overall_feedback="Good form",
            issues=[]
        )
        db.add(form_check)
        db.commit()

    # Test invalid score range
    with pytest.raises(ValueError):
        form_check = FormCheck(
            user_id=test_user.id,
            exercise_type="squat",
            video_url="https://example.com/video.mp4",
            score=101,  # Score should be 0-100
            overall_feedback="Good form",
            issues=[]
        )
        db.add(form_check)
        db.commit()

def test_user_unique_constraints(db: Session):
    # Create initial user
    user1 = User(
        email="user@example.com",
        username="user1",
        hashed_password=get_password_hash("password"),
        subscription_tier="free",
        subscription_end_date=datetime.now() + timedelta(days=30),
        is_email_verified=True
    )
    db.add(user1)
    db.commit()

    # Try to create user with same email
    with pytest.raises(Exception):  # SQLAlchemy will raise an integrity error
        user2 = User(
            email="user@example.com",  # Same email
            username="user2",
            hashed_password=get_password_hash("password"),
            subscription_tier="free",
            subscription_end_date=datetime.now() + timedelta(days=30),
            is_email_verified=True
        )
        db.add(user2)
        db.commit()

    # Try to create user with same username
    with pytest.raises(Exception):
        user3 = User(
            email="user3@example.com",
            username="user1",  # Same username
            hashed_password=get_password_hash("password"),
            subscription_tier="free",
            subscription_end_date=datetime.now() + timedelta(days=30),
            is_email_verified=True
        )
        db.add(user3)
        db.commit()

def test_form_check_timestamps(db: Session, test_user: User):
    form_check = FormCheck(
        user_id=test_user.id,
        exercise_type="squat",
        video_url="https://example.com/video.mp4",
        score=85,
        overall_feedback="Good form",
        issues=[]
    )
    db.add(form_check)
    db.commit()
    db.refresh(form_check)

    assert form_check.created_at is not None
    assert isinstance(form_check.created_at, datetime)
    assert (datetime.now() - form_check.created_at).total_seconds() < 5  # Created within last 5 seconds 