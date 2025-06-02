from fastapi import FastAPI, Request, HTTPException, Depends
import httpx
from fastapi.responses import JSONResponse
import redis.asyncio as redis
from fastapi.middleware.cors import CORSMiddleware

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Assurez-vous que le frontend est accessible
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

USER_SERVICE_URL = "http://user-service:8001"  # Utilisez le nom de service Docker de user-service
CAR_SERVICE_URL = "http://car-service:8002"  # Utilisez le nom de service Docker de car-service
RENTAL_SERVICE_URL = "http://rental-service:8003"  # Utilisez le nom de service Docker de rental-service

@app.post("/users/register")
async def register_user(request: Request):
    data = await request.json()
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{USER_SERVICE_URL}/register", json=data)
        return await response.json()  

@app.post("/users/login")
async def login_user(request: Request):
    data = await request.json()
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{USER_SERVICE_URL}/login", json=data)
        result = await response.json()  

        if response.status_code == 200 and "user_id" in result:
            await redis_client.set(f"gateway:user:{result['user_id']}:session", "active", ex=3600)

        return result

@app.get("/cars")
async def get_all_cars():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{CAR_SERVICE_URL}/cars")
        return await response.json()  # Correction ici

@app.get("/cars/{car_id}")
async def get_car(car_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{CAR_SERVICE_URL}/cars/{car_id}")
        return await response.json()  # Correction ici

@app.post("/cars")
async def create_car(request: Request):
    data = await request.json()
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{CAR_SERVICE_URL}/cars", json=data)
        return await response.json()  # Correction ici

@app.put("/cars/{car_id}/status")
async def update_car_status(car_id: int, request: Request):
    data = await request.json()
    async with httpx.AsyncClient() as client:
        response = await client.put(f"{CAR_SERVICE_URL}/cars/{car_id}/status", json=data)
        return await response.json()  # Correction ici

@app.post("/rentals")
async def create_rental(request: Request):
    data = await request.json()
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{RENTAL_SERVICE_URL}/rentals", json=data)

        if response.status_code >= 400:
            return JSONResponse(
                status_code=response.status_code,
                content=await response.json(),  # Correction ici
            )
        return await response.json()  # Correction ici

@app.get("/rentals")
async def get_all_rentals():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{RENTAL_SERVICE_URL}/rentals")
        return await response.json()  # Correction ici

@app.get("/users/session/{user_id}")
async def check_user_session(user_id: int):
    session = await redis_client.get(f"gateway:user:{user_id}:session")
    if session:
        return {"active": True}
    raise HTTPException(status_code=401, detail="Session expirée ou invalide")

@app.delete("/rentals/{rental_id}")
async def delete_rental(rental_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{RENTAL_SERVICE_URL}/rentals/{rental_id}")
        return await response.json()  # Correction ici

@app.delete("/cars/{car_id}")
async def delete_car(request: Request, car_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{CAR_SERVICE_URL}/cars/{car_id}")
        return await response.json()  # Correction ici

@app.put("/cars/{car_id}")
async def update_car(car_id: int, request: Request):
    data = await request.json()
    async with httpx.AsyncClient() as client:
        response = await client.put(f"{CAR_SERVICE_URL}/cars/{car_id}", json=data)
        return await response.json()  # Correction ici

@app.get("/admin/users")
async def get_users():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{USER_SERVICE_URL}/users")
        return await response.json()  # Correction ici

@app.get("/admin/users/{user_id}")
async def get_user(user_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{USER_SERVICE_URL}/users/{user_id}")
        return await response.json()  # Correction ici
