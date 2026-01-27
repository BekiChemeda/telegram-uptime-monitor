from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from app.database.init_db import init_db
from app.routers import checks, monitors, users
from app.services.scheduler import start_scheduler
from app.bot.main import start_bot

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    
    # Start the scheduler in the background
    scheduler_task = asyncio.create_task(start_scheduler())
    
    # Start the bot in the background
    bot_task = asyncio.create_task(start_bot())

    yield
    
    # Cancel the scheduler on shutdown
    scheduler_task.cancel()
    
    # Stop the bot (polling) - Telebot doesn't have a clean stop for async polling in the same way, 
    # but cancelling the task usually works or it stops when event loop closes.
    bot_task.cancel()
    
    try:
        await scheduler_task
        await bot_task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Uptime Monitor API"}

@app.get("/health")
async def get_health():
    return {"status": "ok"}


app.include_router(users.router)
app.include_router(monitors.router)
app.include_router(checks.router)