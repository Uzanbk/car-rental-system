from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, select, Float
from typing import AsyncGenerator, List
from pydantic import BaseModel
import redis.asyncio as redis
from fastapi.middleware.cors import CORSMiddleware

DATABASE_URL = "postgresql+asyncpg://postgres:eya1234@postgres-cars:5432/cars_db"


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

class CarModel(Base):
    __tablename__ = 'cars'

    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String)
    model = Column(String)
    year = Column(Integer, nullable=True)
    price_per_day = Column(Float, nullable=True)
    mileage = Column(Integer, nullable=True)
    location = Column(String, nullable=True)
    is_rented = Column(Boolean, default=False)
    type = Column(String, nullable=True)
    image_url = Column(String, nullable=True)

class Car(BaseModel):
    id: int
    brand: str
    model: str
    year: int
    price_per_day: float
    mileage: int
    location: str
    type: str
    is_rented: bool
    image_url: str | None = None

    class Config:
        orm_mode = True

class CarCreate(BaseModel):
    brand: str
    model: str
    year: int
    price_per_day: float
    mileage: int
    location: str
    type: str
    image_url: str | None = None

class CarUpdate(CarCreate):
    is_rented: bool  

class CarStatusUpdate(BaseModel):
    is_rented: bool

@app.get("/cars", response_model=List[Car])
async def list_cars(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CarModel))
    return result.scalars().all()

@app.post("/cars", response_model=Car)
async def create_car(car: CarCreate, db: AsyncSession = Depends(get_db)):
    new_car = CarModel(
        brand=car.brand,
        model=car.model,
        year=car.year,
        price_per_day=car.price_per_day,
        mileage=car.mileage,
        location=car.location,
        image_url=car.image_url,
        type=car.type,
        is_rented=False,
    )
    db.add(new_car)
    await db.commit()
    await db.refresh(new_car)
    await redis_client.set(f"car_status:{new_car.id}", "available")
    return new_car

@app.put("/cars/{car_id}", response_model=Car)
async def update_car(car_id: int, car_data: CarUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CarModel).where(CarModel.id == car_id))
    car = result.scalar_one_or_none()
    if car is None:
        raise HTTPException(status_code=404, detail="Voiture non trouvée")

    for field, value in car_data.dict().items():
        setattr(car, field, value)

    await db.commit()
    await db.refresh(car)
    redis_status = "rented" if car.is_rented else "available"
    await redis_client.set(f"car_status:{car_id}", redis_status)
    return car

@app.put("/cars/{car_id}/status", response_model=Car)
async def update_car_status(car_id: int, status: CarStatusUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CarModel).where(CarModel.id == car_id))
    car = result.scalar_one_or_none()
    if car is None:
        raise HTTPException(status_code=404, detail="Voiture non trouvée")

    car.is_rented = status.is_rented
    await db.commit()
    await db.refresh(car)

    redis_status = "rented" if status.is_rented else "available"
    await redis_client.set(f"car_status:{car_id}", redis_status)

    return car

@app.delete("/cars/{car_id}")
async def delete_car(car_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CarModel).where(CarModel.id == car_id))
    car = result.scalar_one_or_none()
    if car is None:
        raise HTTPException(status_code=404, detail="Voiture non trouvée")

    await db.delete(car)
    await db.commit()
    await redis_client.delete(f"car_status:{car_id}")
    return {"message": "Voiture supprimée avec succès"}














@app.get("/cars/{car_id}", response_model=Car)
async def get_car(car_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CarModel).where(CarModel.id == car_id))
    car = result.scalar_one_or_none()
    if car is None:
        raise HTTPException(status_code=404, detail="Voiture non trouvée")
    return car