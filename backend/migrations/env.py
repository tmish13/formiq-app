"""Alembic environment module."""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import event

from alembic import context
from dotenv import load_dotenv

# Add the project's parent directory to sys.path to allow importing 'app'
# This assumes that env.py is in a directory like 'backend/alembic' 
# and 'app' is in 'backend/app'.
# Adjust the number of 'os.path.join(..., "..")' if your structure is different.
current_script_path = os.path.dirname(os.path.abspath(__file__))
project_root_containing_app = os.path.abspath(os.path.join(current_script_path, "..")) 
# If 'app' is directly inside the directory that 'alembic' is in (e.g. backend/app, backend/alembic)
# then project_root_containing_app should be this directory.
# If 'app' is one level above where 'alembic' script dir is (e.g. root/app, root/backend/alembic)
# then it should be os.path.join(current_script_path, "..", "..")

if project_root_containing_app not in sys.path:
    sys.path.insert(0, project_root_containing_app)

# --- BEGIN SIMPLIFIED URL AND ENV LOADING ---

# Path to .env file: env.py is in backend/alembic/, .env should be in backend/
# current_script_dir = os.path.dirname(os.path.abspath(__file__)) # Not needed if logic changes
# dotenv_path = os.path.join(current_script_dir, "..", ".env") # Not needed if logic changes

# print(f"DEBUG: env.py - Attempting to load .env from: {dotenv_path}") # Keep for CLI context if needed
# if os.path.exists(dotenv_path):
# load_dotenv(dotenv_path)
# print(f"DEBUG: env.py - Successfully loaded .env from: {dotenv_path}")
# else:
# print(f"DEBUG: env.py - .env file not found at {dotenv_path}. Will use defaults or existing env vars.")

# Construct the DATABASE_URL directly using os.getenv
# DB_USER = os.getenv("POSTGRES_USER", "postgres")
# DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres") # Be careful with printing passwords
# env_postgres_server = os.getenv("POSTGRES_SERVER")
# if env_postgres_server == "db":
# DB_SERVER = "localhost"
# else:
# DB_SERVER = env_postgres_server if env_postgres_server else "localhost"
# DB_PORT = os.getenv("POSTGRES_PORT", "5432")
# DB_NAME = os.getenv("POSTGRES_DB", "formiq_db") # This should match your target DB
# ACTUAL_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_NAME}"
# print(f"DEBUG: env.py - Constructed DATABASE_URL for Alembic: postgresql://{DB_USER}:<password_hidden>@{DB_SERVER}:{DB_PORT}/{DB_NAME}")

# --- END SIMPLIFIED URL AND ENV LOADING ---

# This is the Alembic Config object.
config = context.config

# Check if sqlalchemy.url is already set (e.g., by programmatic call)
# and if it's not the placeholder from alembic.ini
existing_url = config.get_main_option("sqlalchemy.url")
# The placeholder_url should exactly match what's in alembic.ini initially
# If alembic.ini might have a different placeholder or be empty for sqlalchemy.url, adjust this.
placeholder_url_from_ini = "postgresql://user:password@host:port/dbname_placeholder" 

if not existing_url or existing_url.strip() == placeholder_url_from_ini.strip():
    print(f"DEBUG: env.py - sqlalchemy.url ('{existing_url}') is not set or is placeholder. Attempting to load from .env for CLI.")
    # --- .env loading logic for CLI Alembic runs ---
    current_script_dir_for_env = os.path.dirname(os.path.abspath(__file__))
    dotenv_path_for_cli = os.path.join(current_script_dir_for_env, "..", ".env") # Should point to backend/.env
    
    print(f"DEBUG: env.py (CLI context) - Attempting to load .env from: {dotenv_path_for_cli}")
    if os.path.exists(dotenv_path_for_cli):
        load_dotenv(dotenv_path_for_cli)
        print(f"DEBUG: env.py (CLI context) - Successfully loaded .env from: {dotenv_path_for_cli}")
    else:
        print(f"DEBUG: env.py (CLI context) - .env file not found at {dotenv_path_for_cli}. Will use defaults or existing env vars.")

    cli_db_user = os.getenv("POSTGRES_USER", "postgres")
    cli_db_password = os.getenv("POSTGRES_PASSWORD", "postgres")
    cli_env_postgres_server = os.getenv("POSTGRES_SERVER")
    cli_db_server = "localhost" if cli_env_postgres_server == "db" else (cli_env_postgres_server or "localhost")
    cli_db_port = os.getenv("POSTGRES_PORT", "5432")
    cli_db_name = os.getenv("POSTGRES_DB", "formiq_db") # Ensure this matches the target
    
    cli_actual_database_url = f"postgresql://{cli_db_user}:{cli_db_password}@{cli_db_server}:{cli_db_port}/{cli_db_name}"
    print(f"DEBUG: env.py (CLI context) - Constructed DATABASE_URL: postgresql://{cli_db_user}:<password_hidden>@{cli_db_server}:{cli_db_port}/{cli_db_name}")
    
    if cli_actual_database_url: # Ensure it was actually constructed
        config.set_main_option("sqlalchemy.url", cli_actual_database_url)
        db_password_to_print_cli = cli_db_password if cli_db_password else ""
        url_for_print_cli = config.get_main_option('sqlalchemy.url').replace(db_password_to_print_cli, '**********') if db_password_to_print_cli else config.get_main_option('sqlalchemy.url')
        print(f"DEBUG: env.py (CLI context) - Forcibly set config.sqlalchemy.url to: {url_for_print_cli}")
    else:
        print("DEBUG: env.py (CLI context) - Failed to construct DATABASE_URL from .env. alembic.ini placeholder might be used if not overridden by caller.")
else:
    # Attempt to hide password if it's postgres for printing existing_url
    # This is a simple replacement; more robust parsing might be needed if URLs are complex
    temp_url_for_print = existing_url
    if "postgresql://" in temp_url_for_print and ":" in temp_url_for_print.split("@")[0]:
        user_pass_part = temp_url_for_print.split("://")[1].split("@")[0]
        if ":" in user_pass_part:
            password_to_hide = user_pass_part.split(":")[1]
            if password_to_hide: # ensure there is a password part
                 temp_url_for_print = temp_url_for_print.replace(f':{password_to_hide}@', ':**********@')
    print(f"DEBUG: env.py - sqlalchemy.url already set to a non-placeholder value by caller: '{temp_url_for_print}'. Using this URL.")


# Interpret the config file for Python logging ONLY.
# This is often problematic if the URL is not what fileConfig expects for DB logging handlers.
# Consider making logging setup more robust or conditional.
logging_config_file = config.config_file_name
if logging_config_file is not None:
    try:
        print(f"DEBUG: env.py - Attempting to apply logging configuration from: {logging_config_file} using fileConfig.")
        fileConfig(logging_config_file, disable_existing_loggers=False)
        print(f"DEBUG: env.py - Successfully applied logging config from {logging_config_file}.")
    except Exception as e:
        # This is where the KeyError: 'formatters' likely occurs.
        # If sqlalchemy.url is for SQLite, but alembic.ini has logging expecting PostgreSQL, it can fail.
        print(f"DEBUG: env.py - WARNING: Failed to apply logging config from {logging_config_file} with fileConfig. Error: {e}")
        print(f"DEBUG: env.py - Current sqlalchemy.url during logging config attempt: {config.get_main_option('sqlalchemy.url')}")
        print("DEBUG: env.py - Skipping fileConfig due to error. Basic logging will be used.")
        # Fallback to basic logging configuration if fileConfig fails
        import logging.config
        logging.basicConfig(level=logging.INFO) # Or logging.DEBUG for more verbosity
        logging.getLogger('alembic').setLevel(logging.INFO) # Ensure Alembic's own logger is at a reasonable level
        print("DEBUG: env.py - Applied basicConfig for logging as a fallback.")


# Add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# Example for your project (ensure your models are imported so Base.metadata is populated):
from app.models.base import BaseModel # Or your actual base model that all models inherit

# --- Ensure all active SQLAlchemy models are imported here ---
# So that BaseModel.metadata (which is Base.metadata) knows about all tables.
from app.models.user import User
from app.models.user_session import UserSession # The consolidated session model
from app.models.video import Video
from app.models.form_check import FormCheck, FeedbackItem # Assuming FeedbackItem is also a table
from app.models.exercise import ExerciseTemplate
from app.models.exercise_config import ExerciseConfig
from app.models.user_settings import UserSettings

# If you have other active models that define tables, import them too.
# For example, if 'Subscription', 'Workout', etc., are still active, they should be here.
# If they are being removed, their absence here (and in your models directory later)
# will signal Alembic to generate drop_table operations if the tables exist.
# For now, focusing on models confirmed or likely to be part of the core AI pipeline and infra.

# Removed original example imports as they are now covered above or are illustrative.
# from app.models.user import User # Assuming User model exists - Covered
# from app.models.video import Video # Assuming Video model exists - Covered
# ... import other models ...

target_metadata = BaseModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired: 
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")

    # Check if the dialect is SQLite for batch mode based on URL, as no engine/connection here
    # This is a simplification; a more robust check might involve parsing the URL
    # or ensuring this mode is not used with SQLite if batch is needed.
    is_sqlite_offline = url is not None and url.startswith("sqlite")

    if is_sqlite_offline:
        print("DEBUG: env.py (offline) - SQLite dialect detected, enabling render_as_batch=True")
        context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            render_as_batch=True # Enable batch mode for SQLite
        )
    else:
        print(f"DEBUG: env.py (offline) - Dialect (from URL: {url}) is not SQLite or URL is None, not enabling batch mode.")
        context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # engine_from_config will use the sqlalchemy.url we set on the config object
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}), # This will use the [alembic] section
        prefix="sqlalchemy.",                               # and pick up the overridden sqlalchemy.url
        poolclass=pool.NullPool,
    )

    # Add event listener for PRAGMA foreign_keys=ON for SQLite
    if connectable.dialect.name == "sqlite":
        @event.listens_for(connectable, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
                print("DEBUG: env.py - PRAGMA foreign_keys=ON executed for SQLite connection.")
            finally:
                cursor.close()

    with connectable.connect() as connection:
        # Check if the dialect is SQLite for batch mode
        if connectable.dialect.name == "sqlite":
            print("DEBUG: env.py - SQLite dialect detected, enabling render_as_batch=True")
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True # Enable batch mode for SQLite
            )
        else:
            print(f"DEBUG: env.py - Dialect is {connectable.dialect.name}, not enabling batch mode.")
            context.configure(
                connection=connection,
                target_metadata=target_metadata
            )
        
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online() 