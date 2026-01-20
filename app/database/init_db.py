import asyncio
from database.connection import engine
from models import Base

async def init_db():
    async with engine.begin() as conn:
        conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(init_db())