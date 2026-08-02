"""
app/worker.py — Async ingestion scheduler for single-table snapshot architecture.
Run this separately from the API: python -m app.worker

Schedule:
  Every 15 min → fetch snapshot for all tracked tickers → UPSERT into PostgreSQL `stocks` table
"""
import asyncio
import structlog
import os
import yfinance as yf
from datetime import datetime, timezone
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.stock import Stock

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=True) if os.getenv("ENVIRONMENT") != "production" else structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

async def get_tracked_tickers() -> list[str]:
    """Fetch all ticker symbols currently in the database."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Stock.ticker))
        return [row[0] for row in result.all()]

async def run_pipeline_once() -> None:
    """Fetch snapshot data for all tickers and update the database."""
    tickers = await get_tracked_tickers()
    if not tickers:
        logger.info("no_tracked_tickers")
        return

    logger.info("pipeline_started", num_tickers=len(tickers), tickers=tickers)

    async def fetch_snapshot(ticker: str):
        try:
            from app.services.stock_scraper import get_stock_snapshot
            return await get_stock_snapshot(ticker, force_refresh=True)
        except Exception as e:
            logger.error("scraper_fetch_error", ticker=ticker, error=str(e))
            return None

    tasks = [fetch_snapshot(t) for t in tickers]
    results = await asyncio.gather(*tasks)

    # Upsert into PostgreSQL
    updated_count = 0
    async with AsyncSessionLocal() as session:
        for res in results:
            if not res:
                continue
            
            # Simple UPSERT
            ticker_val = res.pop("ticker")
            existing = await session.get(Stock, ticker_val)
            if existing:
                for k, v in res.items():
                    setattr(existing, k, v)
            else:
                new_stock = Stock(ticker=ticker_val, **res)
                session.add(new_stock)
            updated_count += 1
            
        await session.commit()

    logger.info("pipeline_completed", updated_tickers=updated_count)


async def main():
    logger.info("worker_started", interval_minutes=15)
    while True:
        try:
            await run_pipeline_once()
        except Exception as e:
            logger.error("pipeline_error", error=str(e), exc_info=True)
        
        await asyncio.sleep(15 * 60)

if __name__ == "__main__":
    asyncio.run(main())
