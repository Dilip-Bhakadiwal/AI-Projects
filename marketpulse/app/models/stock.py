"""app/models/stock.py"""
from datetime import datetime, timezone
from sqlalchemy import String, Float, BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

class Stock(Base):
    __tablename__ = "stocks"

    ticker: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    company_name: Mapped[str] = mapped_column(String, nullable=True)
    
    last_price: Mapped[float] = mapped_column(Float, nullable=True)
    change_val: Mapped[float] = mapped_column(Float, nullable=True)
    change_pct: Mapped[float] = mapped_column(Float, nullable=True)
    
    volume: Mapped[int] = mapped_column(BigInteger, nullable=True)
    open_price: Mapped[float] = mapped_column(Float, nullable=True)
    previous_close: Mapped[float] = mapped_column(Float, nullable=True)
    day_high: Mapped[float] = mapped_column(Float, nullable=True)
    day_low: Mapped[float] = mapped_column(Float, nullable=True)
    
    market_cap: Mapped[int] = mapped_column(BigInteger, nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=True)
    pe_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    high_52week: Mapped[float] = mapped_column(Float, nullable=True)
    low_52week: Mapped[float] = mapped_column(Float, nullable=True)
    dividend_yield: Mapped[float] = mapped_column(Float, nullable=True)
    eps: Mapped[float] = mapped_column(Float, nullable=True)
    exchange: Mapped[str] = mapped_column(String, nullable=True)
    
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<Stock {self.ticker}: {self.last_price}>"
