from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
import secrets
from app.config import API_ACCESS_TOKEN

api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

async def require_api_key(api_key: str = Security(api_key_header)):
    if not API_ACCESS_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API access token is not configured."
        )

    if not api_key or not secrets.compare_digest(api_key, API_ACCESS_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "API-Key"}
        )
    return api_key
