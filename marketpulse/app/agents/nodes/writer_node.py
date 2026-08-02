"""
app/agents/nodes/writer_node.py — Persists analysis results to PostgreSQL.
Writes both ProcessedSignal and AgentLog records.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.analysis.stats_engine import AnalysisResult
from app.database import AsyncSessionLocal
from app.models.agent_log import AgentLog
from app.models.processed_signal import ProcessedSignal

logger = logging.getLogger(__name__)

# LLM cost estimate — Gemma/Llama free tier = $0, but structure is ready for paid models
COST_PER_1K_TOKENS = 0.0  # update when switching to a paid model


async def write_signal(
    stats_result: AnalysisResult,
    llm_result: Optional[dict],
    session_id: str,
) -> int:
    """
    Write ProcessedSignal + AgentLog to PostgreSQL.
    Returns the new ProcessedSignal.id.
    """
    now = datetime.now(timezone.utc)
    tokens = llm_result.get("_tokens", 0) if llm_result else 0
    cost = (tokens / 1000) * COST_PER_1K_TOKENS

    summary = (
        llm_result.get("summary", stats_result.description)
        if llm_result
        else stats_result.description
    )
    model_used = llm_result.get("_model", "stats-only") if llm_result else "stats-only"

    signal = ProcessedSignal(
        ticker=stats_result.ticker,
        analyzed_at=now,
        signal_type=stats_result.signal_type,
        confidence=round(stats_result.confidence, 3),
        summary=summary,
        zscore=round(stats_result.zscore, 4) if stats_result.zscore is not None else None,
        rsi=round(stats_result.rsi, 2) if stats_result.rsi is not None else None,
        price_change_pct=round(stats_result.price_change_pct, 4) if stats_result.price_change_pct is not None else None,
        llm_cost_usd=cost,
        model_used=model_used,
        tokens_used=tokens,
    )

    log = AgentLog(
        session_id=session_id,
        timestamp=now,
        agent_name="analysis_pipeline",
        action="write_signal",
        input_summary=stats_result.description[:500],
        output_summary=summary[:500],
        tokens_used=tokens,
        cost_usd=cost,
    )

    async with AsyncSessionLocal() as session:
        session.add(signal)
        session.add(log)
        await session.commit()
        await session.refresh(signal)

    logger.info(
        "Wrote signal id=%d ticker=%s type=%s",
        signal.id, signal.ticker, signal.signal_type
    )
    return signal.id
