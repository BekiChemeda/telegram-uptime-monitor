from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database.init_db import init_db
from app.routers import users

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Uptime Monitor API"}

@app.get("/health")
async def get_health():
    return {"status": "ok"}


app.include_router(users.router)