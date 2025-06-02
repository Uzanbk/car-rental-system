

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, select
from typing import AsyncGenerator
import redis.asyncio as redis
from passlib.context import CryptContext


redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

DATABASE_URL = "postgresql+asyncpg://postgres:eya1234@postgres:5432/users_db"


Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
    email = Column(String, nullable=False)
    password = Column(String, nullable=False)

class User(BaseModel):
    username: str
    email: str
    password: str


app = FastAPI()

@app.post("/register")
async def create_user(user: User, db: AsyncSession = Depends(get_db)):
    hashed_pw = hash_password(user.password)
    new_user = UserModel(username=user.username, email=user.email, password=hashed_pw)
    db.add(new_user)
    await db.commit()
    return {"message": "Utilisateur créé avec succès"}

@app.post("/login")
async def login_user(data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserModel).where(UserModel.username == data["username"])
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(data["password"], user.password):
        raise HTTPException(status_code=401, detail="Nom d'utilisateur ou mot de passe incorrect")

    await redis_client.set(f"user:{user.id}:session", "active", ex=3600)
    return {"message": "Connexion réussie", "user_id": user.id}




















































@app.get("/users")
async def get_all_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserModel))
    users = result.scalars().all()
    return [user.__dict__ for user in users]

@app.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.__dict__


