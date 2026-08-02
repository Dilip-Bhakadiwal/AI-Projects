from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


class RawTickIn(BaseModel):
    """Validated tick coming from yfinance. Rejects NaN, None, negative prices."""

    ticker: str = Field(..., min_length=1, max_length=10)
    timestamp: datetime
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: int = Field(..., ge=0)
    source: str = "yahoo_finance"

    @field_validator("open", "high", "low", "close", mode="before")
    @classmethod
    def reject_nan(cls, v: float) -> float:
        import math
        if v is None or math.isnan(v) or math.isinf(v):
            raise ValueError("Price field must be a finite number, got NaN/None/Inf")
        return v

    @model_validator(mode="after")
    def high_gte_low(self) -> "RawTickIn":
        """Basic OHLC sanity check — runs after all fields are set."""
        if self.high < self.low:
            raise ValueError(f"high ({self.high}) cannot be less than low ({self.low})")
        return self
