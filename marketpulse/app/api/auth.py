"""
app/api/auth.py — API key authentication middleware.
Protects all routes except /status (health check stays public).
"""
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str = Security(api_key_header)) -> str:
    """FastAPI dependency — raises 403 if API key is missing or wrong."""
    import secrets
    if not api_key or not secrets.compare_digest(api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key. Pass X-API-Key header.",
        )
    return api_key
