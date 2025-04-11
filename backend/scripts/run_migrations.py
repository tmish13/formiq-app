from app.db.base import Base
from app.core.config import settings
from sqlalchemy import create_engine

def run_migrations():
    # Create engine
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    
    # Create all tables
    Base.metadata.create_all(engine)

if __name__ == "__main__":
    run_migrations() 