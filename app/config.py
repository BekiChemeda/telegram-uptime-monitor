from dotenv import load_dotenv
import os

# Load .env file, overriding any existing environment variables
load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env file or environment variables")

print(f"Loaded DATABASE_URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'INVALID'}")