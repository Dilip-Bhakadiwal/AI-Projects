"""app/api/routes/status.py — GET /status (public health check)."""
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import func, select, text

from app.database import AsyncSessionLocal
from app.models.stock import Stock

router = APIRouter()


@router.get("/status", tags=["health"])
async def get_status():
    """
    Public health check. Returns:
    - Database connectivity
    - Tracked stock count
    - Total LLM cost today (for cost awareness)
    - Last ingestion timestamp
    """
    try:
        async with AsyncSessionLocal() as session:
            # Active tickers
            ticker_count = await session.scalar(
                select(func.count(Stock.ticker))
            )

        db_status = "ok"
    except Exception as e:
        return {
            "status": "degraded",
            "database": f"error: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "status": "ok",
        "database": db_status,
        "active_tickers": ticker_count or 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
