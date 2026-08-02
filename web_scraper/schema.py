"""
schema.py — Pydantic output model for stock data.
Every module in the pipeline builds toward this contract.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class StockRecord(BaseModel):
    """Final validated stock record returned to the caller."""

    ticker: str
    name: str
    last_price: float
    change: Optional[float] = None
    pct_change: Optional[float] = None
    volume: Optional[int] = None
    market_cap: Optional[float] = None   # in raw units (e.g. 1_234_567_890)
    pe_ratio: Optional[float] = None
    div_yield: Optional[float] = None    # as a percentage, e.g. 1.5 means 1.5%

    # Metadata — not shown to end user but useful for debugging
    source: str = ""
    field_sources: dict[str, str] = {}
    fetched_at: datetime = None
    confidence: str = "exact"            # "exact" | "fuzzy"
    resolved_exchange: str = ""

    # ------------------------------------------------------------------ #
    # Validators
    # ------------------------------------------------------------------ #

    @field_validator("last_price")
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"last_price must be positive, got {v}")
        return v

    @field_validator("pe_ratio")
    @classmethod
    def pe_must_be_positive_or_none(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            return None   # negative P/E is meaningless; treat as N/A
        return v

    @field_validator("div_yield")
    @classmethod
    def div_yield_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 100):
            return None
        return v

    class Config:
        arbitrary_types_allowed = True


class AdapterResult(BaseModel):
    """Raw result returned by each source adapter before merging."""

    ticker: str
    name: Optional[str] = None
    last_price: Optional[float] = None
    change: Optional[float] = None
    pct_change: Optional[float] = None
    volume: Optional[int] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    div_yield: Optional[float] = None

    source: str
    fetched_at: Optional[datetime] = None
    success: bool = True
    error: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class ResolverResult(BaseModel):
    """Output of the Ticker Resolver stage."""

    symbol: str                          # exchange-qualified, e.g. "ZOMATO.NS"
    exchange: str                        # e.g. "NSE", "NYSE"
    resolved_name: str
    confidence: str = "exact"           # "exact" | "fuzzy"
    candidates: list[dict] = []         # all matches found, for debug / disambiguation
