from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL, DB_ECHO
from urllib.parse import urlparse, parse_qsl

# Parse the database URL to handle connection arguments manually.
parsed_url = urlparse(DATABASE_URL)
connect_args = {}

# Translate sslmode=require to ssl=True for asyncpg compatibility.
query_params = dict(parse_qsl(parsed_url.query))
if query_params.get("sslmode") == "require":
    connect_args["ssl"] = True

# Rebuild the URL without the query string for the engine.
url_for_engine = parsed_url._replace(query="").geturl()

## Create Async Engine
engine = create_async_engine(
    url_for_engine, echo=DB_ECHO, connect_args=connect_args
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
