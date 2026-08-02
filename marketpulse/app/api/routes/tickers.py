"""app/api/routes/tickers.py — CRUD for user-registered tickers."""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.auth import require_api_key
from app.database import AsyncSessionLocal
from app.models.stock import Stock
from app.agents.query_agent.tools.db_write import add_stock

router = APIRouter(prefix="/tickers", tags=["tickers"])


class TickerCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10, description="Stock symbol e.g. AAPL")


class StockResponse(BaseModel):
    ticker: str
    company_name: Optional[str] = None
    last_price: Optional[float] = None
    change_val: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[int] = None
    market_cap: Optional[int] = None
    currency: Optional[str] = None
    exchange: Optional[str] = None
    last_updated: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[StockResponse])
async def list_tickers(_: str = Depends(require_api_key)):
    """List all registered stocks."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Stock).order_by(Stock.ticker))
        stocks = result.scalars().all()
    return stocks


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_ticker(body: TickerCreate, _: str = Depends(require_api_key)):
    """Register a new ticker for tracking and fetch its initial snapshot."""
    ticker_upper = body.ticker.upper().strip()

    # Reuse the tool logic to fetch and insert
    result = await add_stock.ainvoke({"ticker": ticker_upper})
    
    if "Failed" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result,
        )

    return {"status": "success", "message": result}


@router.delete("/{ticker}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticker(ticker: str, _: str = Depends(require_api_key)):
    """Delete a ticker from the database."""
    ticker_upper = ticker.upper().strip()

    async with AsyncSessionLocal() as session:
        existing = await session.scalar(
            select(Stock).where(Stock.ticker == ticker_upper)
        )
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticker {ticker_upper} not found",
            )

        await session.delete(existing)
        await session.commit()
