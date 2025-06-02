from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Date, select
from typing import AsyncGenerator, Optional
from datetime import date
import redis.asyncio as redis
import httpx


DATABASE_URL = "postgresql+asyncpg://postgres:eya1234@postgres-rentals:5432/rental_db"

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()


redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)


class RentalModel(Base):
    __tablename__ = "rentals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    car_id = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String, default="ongoing")

class Rental(BaseModel):
    user_id: int
    car_id: int
    start_date: date
    end_date: date
    status: Optional[str] = "ongoing"


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


app = FastAPI()

@app.post("/rentals")
async def create_rental(rental: Rental, db: AsyncSession = Depends(get_db)):
    if not rental.start_date or not rental.end_date:
        raise HTTPException(status_code=422, detail="Dates invalides")
    
    redis_key = f"car_status:{rental.car_id}"
    status = await redis_client.get(redis_key)
    if status == "rented":
        raise HTTPException(status_code=400, detail="Voiture déjà louée (cache)")
  
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://localhost:8000/cars/{rental.car_id}")
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Voiture non trouvée")

        car_data = response.json()
        if car_data.get("is_rented"):
            await redis_client.set(redis_key, "rented")
            raise HTTPException(status_code=400, detail="Voiture déjà louée (car service)")

    
    new_rental = RentalModel(
        user_id=rental.user_id,
        car_id=rental.car_id,
        start_date=rental.start_date,
        end_date=rental.end_date,
        status=rental.status or "ongoing")
    db.add(new_rental)
    await db.commit()  
    async with httpx.AsyncClient() as client:
        update_response = await client.put(
            f"http://localhost:8000/cars/{rental.car_id}/status",
            json={"is_rented": True}
        )
        if update_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour du statut de la voiture")
    status = await redis_client.get(redis_key)
    await redis_client.set(redis_key, "rented")

    return {"message": "Voiture louée avec succès"}

































@app.get("/rentals")
async def get_all_rentals(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RentalModel))
    rentals = result.scalars().all()
    return [r.__dict__ for r in rentals]