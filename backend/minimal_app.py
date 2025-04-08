"""Minimal app to test SQLAlchemy with SQLite."""
import os
from typing import Optional, List, AsyncGenerator
import uvicorn
import asyncio
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy.pool import NullPool
from sqlalchemy.future import select
from pydantic import BaseModel
import contextlib

# SQLite file
DB_FILE = "./minimal_test.db"

# Remove the existing database file if it exists
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
    print(f"Removed existing database file: {DB_FILE}")

# Create a Base class for SQLAlchemy models
Base = declarative_base()

# Define a User model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=True)
    password = Column(String, nullable=False)

# Pydantic models for API
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    
    class Config:
        from_attributes = True

# Create engine with aiosqlite
engine = create_async_engine(
    f"sqlite+aiosqlite:///{DB_FILE}",
    poolclass=NullPool,
    echo=True,
    connect_args={"check_same_thread": False}
)

# Create session
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for the application."""
    # --- STARTUP LOGIC ---
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created")
    
    # Yield control to FastAPI
    yield
    
    # --- SHUTDOWN LOGIC ---
    # Close database connections
    await engine.dispose()
    print("Engine disposed")

# Modify FastAPI app to use the lifespan context manager
app = FastAPI(
    title="FastAPI Minimal Example",
    description="A minimal FastAPI application with SQLAlchemy",
    lifespan=lifespan
)

# Dependency for database session
async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

# Register endpoint
@app.post("/auth/register", response_model=UserResponse)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # Check if user exists
    result = await db.execute(
        select(User.id).where(User.email == user_in.email)
    )
    if result.scalars().first():
        raise HTTPException(400, "Email already registered")
        
    # Create user
    new_user = User(
        email=user_in.email,
        password=user_in.password,  # In a real app, you'd hash this
        full_name=user_in.full_name
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

# Get all users endpoint
@app.get("/auth/users", response_model=List[UserResponse])
async def get_users(db: AsyncSession = Depends(get_db)):
    """Get all users."""
    result = await db.execute(
        select(User.id, User.email, User.full_name)
    )
    users = [{"id": id, "email": email, "full_name": full_name} 
             for id, email, full_name in result]
    return users

# Get user by ID endpoint
@app.get("/auth/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get user by ID."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(404, "User not found")
    return user

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 