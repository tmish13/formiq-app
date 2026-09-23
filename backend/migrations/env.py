"""Alembic environment module."""
import os
import sys

# Ensure the package directory ('backend' in this case, which contains 'app') is in sys.path
# This allows 'from app...' imports to work correctly.
# Assuming env.py is in backend/migrations/
PACKAGE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PACKAGE_ROOT not in sys.path:
    sys.path.insert(0, PACKAGE_ROOT)

# If you also need the true project root ('formiq-app-3') for some reason,
# e.g. if you had imports like 'from backend.app...', although 'from app...' is more common
# when the 'backend' directory itself is the main source root for the backend package.
# TRUE_PROJECT_ROOT = os.path.abspath(os.path.join(PACKAGE_ROOT, '..'))
# if TRUE_PROJECT_ROOT not in sys.path:
#     sys.path.insert(0, TRUE_PROJECT_ROOT)

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
# current_script_path = os.path.dirname(os.path.abspath(__file__))
# project_root_containing_app = os.path.abspath(os.path.join(current_script_path, "..")) 
# # If 'app' is directly inside the directory that 'alembic' is in (e.g. backend/app, backend/alembic)
# # then project_root_containing_app should be this directory.
# # If 'app' is one level above where 'alembic' script dir is (e.g. root/app, root/backend/alembic)
# # then it should be os.path.join(current_script_path, "..", "..")

# if project_root_containing_app not in sys.path:
# sys.path.insert(0, project_root_containing_app)

# backend/migrations/env.py
# Add the project root directory ('formiq-app-3') to sys.path
# This allows imports like 'from backend.app...' or 'from app...' if 'backend' is the top-level package recognized
current_dir = os.path.dirname(os.path.abspath(__file__)) # This is /Users/tarpanmishra/formiq-app-3/backend/migrations
project_backend_root = os.path.abspath(os.path.join(current_dir, '..')) # This is /Users/tarpanmishra/formiq-app-3/backend
project_true_root = os.path.abspath(os.path.join(project_backend_root, '..')) # This is /Users/tarpanmishra/formiq-app-3

if project_backend_root not in sys.path:
    sys.path.insert(0, project_backend_root) # Ensures 'app' can be found as 'app' if CWD is 'backend'

# Sometimes, especially if running alembic from the true project root,
# or if other modules expect to import 'backend.app', having the true root is also good.
#
# APPEND, do not insert(0): the backend root must keep priority on sys.path.
# In the container the backend directory is mounted at /app, so project_true_root
# is "/". Because backend/__init__.py exists, prepending "/" made `import app`
# resolve to /app (the backend package) instead of /app/app, and every migration
# failed with "ModuleNotFoundError: No module named 'app.models'".
# This affected `alembic upgrade head` in docker-entrypoint.sh:33 as well.
if project_true_root not in sys.path:
    sys.path.append(project_true_root)

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
# --- Resolve database URL from POSTGRES_* env vars (same source as app config) ---
existing_url = config.get_main_option("sqlalchemy.url")
placeholder_url_from_ini = "postgresql://user:password@host:port/dbname_placeholder"

if not existing_url or existing_url.strip() == placeholder_url_from_ini.strip():
    # Load .env for CLI runs (programmatic callers set sqlalchemy.url directly)
    dotenv_path = os.path.join(project_backend_root, ".env")
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)

    db_user = os.getenv("POSTGRES_USER", "postgres")
    db_password = os.getenv("POSTGRES_PASSWORD", "postgres")
    db_server = os.getenv("POSTGRES_SERVER", "localhost")
    if db_server == "db":
        # "db" is the compose service alias. It resolves INSIDE the container but
        # not on the host, so only fall back to localhost when it genuinely does
        # not resolve. The previous unconditional rewrite made `alembic upgrade`
        # impossible to run inside the container (and broke the `alembic upgrade
        # head` step in docker-entrypoint.sh:33).
        import socket
        try:
            socket.getaddrinfo(db_server, None)
        except socket.gaierror:
            db_server = "localhost"  # host-side run: use the published port
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "formiq")

    database_url = f"postgresql://{db_user}:{db_password}@{db_server}:{db_port}/{db_name}"
    config.set_main_option("sqlalchemy.url", database_url)
    print(f"DEBUG: env.py - Using POSTGRES_* vars → postgresql://{db_user}:***@{db_server}:{db_port}/{db_name}")


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
from app.models.telemetry import PostureV1InferenceLog
# Registered HERE as well as in app/models/__init__.py. env.py keeps its own
# import block, and a model missing from it is invisible to autogenerate --
# which shows up as alembic proposing to DROP a table that is in use.
from app.models.audit import AnalysisRun, CheckerDecision

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