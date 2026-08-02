"""
app/models/agent_log.py — Tracks every agent action for observability.
Each row = one tool invocation or LLM call in the pipeline.
"""
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    agent_name: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)

    input_summary: Mapped[str] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str] = mapped_column(Text, nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=True)

    tokens_used: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)

    def __repr__(self):
        return f"<AgentLog {self.id} {self.agent_name}/{self.action}>"
