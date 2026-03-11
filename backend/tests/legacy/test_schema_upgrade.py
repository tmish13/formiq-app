import sqlalchemy as sa
from sqlalchemy import inspect, create_engine

def test_database_schema():
    # Note: Ensure the database URL points to the correct test/dev database
    # Using postgres default db for inspection might be okay if user/pass are right,
    # but ideally connect to the actual 'formiq' db if possible.
    # Using 'formiq' as the database name based on alembic.ini
    engine = create_engine("postgresql://postgres:postgres@localhost:5432/formiq")
    inspector = inspect(engine)

    expected_tables = [
        "users", "videos", "form_checks", 
        "workouts", "workout_plans", "subscriptions",
        "exercises", # Check if this replaces workout_exercises
        "exercise_templates", "exercise_configs",
        "user_sessions", "user_settings", "feedback_items",
        "alembic_version" # Should also exist
    ]
    actual_tables = inspector.get_table_names()
    print(f"Actual tables found: {actual_tables}") # Added print for debugging
    for table in expected_tables:
        assert table in actual_tables, f"{table} table missing!"

    # Check specific indexes known to be important
    user_indexes = {i["name"] for i in inspector.get_indexes("users")}
    print(f"Indexes found on users table: {user_indexes}") # Added print for debugging
    assert "ix_users_email" in user_indexes, "Missing index: ix_users_email"
    assert "ix_users_username" in user_indexes, "Missing index: ix_users_username"

    # Add more index checks as needed for other tables
    video_indexes = {i["name"] for i in inspector.get_indexes("videos")}
    # Example check (add specific index names if known)
    # assert "ix_videos_user_id" in video_indexes, "Missing index on videos table"

    # Check alembic version table explicitly
    assert "alembic_version" in actual_tables, "alembic_version table missing!" 