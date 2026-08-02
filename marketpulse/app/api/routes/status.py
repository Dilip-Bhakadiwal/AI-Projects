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
        err_str = str(e)
        if "Errno -2" in err_str or "111" in err_str or "Connection refused" in err_str or "shut down" in err_str:
            db_msg = "Aiven Free-Tier DB Sleeping (Auto-wakes on request)"
        else:
            db_msg = f"error: {err_str}"
        return {
            "status": "degraded",
            "database": db_msg,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "status": "ok",
        "database": db_status,
        "active_tickers": ticker_count or 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
