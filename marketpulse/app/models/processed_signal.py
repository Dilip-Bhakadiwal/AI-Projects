"""
app/models/processed_signal.py — Stores the output of the analysis pipeline.
One row per ticker per analysis run.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProcessedSignal(Base):
    __tablename__ = "processed_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, nullable=False, index=True)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    signal_type: Mapped[str] = mapped_column(String, nullable=False)  # "normal" | "anomaly"
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)

    zscore: Mapped[float] = mapped_column(Float, nullable=True)
    rsi: Mapped[float] = mapped_column(Float, nullable=True)
    price_change_pct: Mapped[float] = mapped_column(Float, nullable=True)

    llm_cost_usd: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    model_used: Mapped[str] = mapped_column(String, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=True, default=0)

    def __repr__(self):
        return f"<ProcessedSignal {self.id} {self.ticker} {self.signal_type}>"
