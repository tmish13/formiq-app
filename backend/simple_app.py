from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import sqlite3
import os
from pydantic import BaseModel

# Create database file if it doesn't exist
db_file = "simple_test.db"
if not os.path.exists(db_file):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('''CREATE TABLE users
                 (id INTEGER PRIMARY KEY, email TEXT, full_name TEXT, password TEXT)''')
    conn.commit()
    conn.close()

# Define FastAPI app
app = FastAPI(title="Simple Auth API")

# Create async engine with SQLite
DATABASE_URL = f"sqlite+aiosqlite:///./{db_file}"
engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=NullPool,
    echo=True
)

# Create async session
async_session = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Dependency to get async session
async def get_session():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

# Request models
class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str

class UserResponse(BaseModel):
    email: str
    full_name: str

# Routes
@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/register", response_model=UserResponse)
async def register(user: UserCreate, session: AsyncSession = Depends(get_session)):
    # Check if user already exists
    query = f"SELECT email FROM users WHERE email = '{user.email}'"
    result = await session.execute(query)
    if result.fetchone():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Insert new user
    query = f"""
    INSERT INTO users (email, full_name, password) 
    VALUES ('{user.email}', '{user.full_name}', '{user.password}')
    """
    await session.execute(query)
    await session.commit()
    
    return UserResponse(email=user.email, full_name=user.full_name)

@app.get("/users")
async def get_users(session: AsyncSession = Depends(get_session)):
    query = "SELECT email, full_name FROM users"
    result = await session.execute(query)
    users = result.fetchall()
    return [{"email": email, "full_name": full_name} for email, full_name in users]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 