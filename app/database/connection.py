from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL, DB_ECHO


## Create Async Engine
engine = create_async_engine(
    DATABASE_URL, echo=DB_ECHO
)


# Create Session Factory

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
## Define Dependency for FastAPI
async def get_db():
    async with async_session() as session:
        yield session
