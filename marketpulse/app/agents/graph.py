"""
app/agents/graph.py — LangGraph state machine for the analysis pipeline.

Flow:
  fetch_data → stats_analysis → [conditional edge] → llm_synthesis → write_result
                                       ↓
                               (no anomaly, confidence low)
                                       ↓
                                 skip_llm → write_result

This is the honest architecture: stats decide WHAT, LLM explains WHY.
"""
import logging
import uuid
from typing import List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.analysis.stats_engine import AnalysisResult, analyse_ticker
from app.agents.nodes.analyst_node import run_analyst_node
from app.agents.nodes.writer_node import write_signal

logger = logging.getLogger(__name__)

# ── State schema ──────────────────────────────────────────────────────────────

class AnalysisState(TypedDict):
    ticker: str
    closes: List[float]
    volumes: List[int]
    session_id: str
    stats_result: Optional[AnalysisResult]
    llm_result: Optional[dict]
    signal_id: Optional[int]
    error: Optional[str]


# ── Node functions ────────────────────────────────────────────────────────────

def stats_node(state: AnalysisState) -> AnalysisState:
    """Run statistical analysis — no LLM, no network call."""
    try:
        result = analyse_ticker(
            ticker=state["ticker"],
            closes=state["closes"],
            volumes=state["volumes"],
        )
        state["stats_result"] = result
        state["error"] = None
    except Exception as e:
        logger.error("Stats node failed for %s: %s", state["ticker"], e)
        state["error"] = str(e)
    return state


async def llm_node(state: AnalysisState) -> AnalysisState:
    """Call LLM to explain the anomaly — only reached via conditional edge."""
    stats = state["stats_result"]
    if stats is None:
        return state
    try:
        result = await run_analyst_node(stats)
        state["llm_result"] = result
    except Exception as e:
        logger.error("LLM node failed for %s: %s", state["ticker"], e)
        state["llm_result"] = None
    return state


def skip_llm_node(state: AnalysisState) -> AnalysisState:
    """No anomaly detected — skip LLM, save API quota."""
    state["llm_result"] = None
    logger.info("Skipping LLM for %s (no anomaly detected)", state["ticker"])
    return state


async def write_node(state: AnalysisState) -> AnalysisState:
    """Write result to PostgreSQL."""
    stats = state["stats_result"]
    if stats is None:
        if state.get("error"):
            # MISCON-03 fix: write the error to AgentLog
            from app.database import AsyncSessionLocal
            from app.models.agent_log import AgentLog
            from datetime import datetime, timezone
            try:
                async with AsyncSessionLocal() as session:
                    log_entry = AgentLog(
                        session_id=state["session_id"],
                        timestamp=datetime.now(timezone.utc),
                        agent_name="stats_node",
                        action="error",
                        details={"error": state["error"], "ticker": state["ticker"]}
                    )
                    session.add(log_entry)
                    await session.commit()
            except Exception as db_e:
                logger.error("Failed to write error state for %s: %s", state["ticker"], db_e)
        return state
    try:
        signal_id = await write_signal(
            stats_result=stats,
            llm_result=state.get("llm_result"),
            session_id=state["session_id"],
        )
        state["signal_id"] = signal_id
    except Exception as e:
        logger.error("Write node failed for %s: %s", state["ticker"], e)
        state["error"] = str(e)
    return state


# ── Conditional edge ─────────────────────────────────────────────────────────

def route_after_stats(state: AnalysisState) -> str:
    """
    Core branching logic:
    - Anomaly detected AND confidence > 0.4 → call LLM for explanation
    - Normal trend or low confidence → skip LLM, go straight to write
    """
    stats = state.get("stats_result")
    if state.get("error"):
        return "skip_llm"  # still write the error state (routes through skip_llm to write)
    if stats and stats.has_anomaly and stats.confidence > 0.4:
        logger.info(
            "Routing %s → LLM (anomaly=True, confidence=%.2f)",
            state["ticker"], stats.confidence
        )
        return "llm"
    return "skip_llm"


# ── Build the graph ───────────────────────────────────────────────────────────

def build_analysis_graph():
    """Build and compile the LangGraph state machine."""
    graph = StateGraph(AnalysisState)

    # Nodes
    graph.add_node("stats", stats_node)
    graph.add_node("llm", llm_node)
    graph.add_node("skip_llm", skip_llm_node)
    graph.add_node("write", write_node)

    # Edges
    graph.add_edge(START, "stats")
    graph.add_conditional_edges(
        "stats",
        route_after_stats,
        {"llm": "llm", "skip_llm": "skip_llm"},
    )
    graph.add_edge("llm", "write")
    graph.add_edge("skip_llm", "write")
    graph.add_edge("write", END)

    return graph.compile()


# Singleton — compiled once at import time
analysis_graph = build_analysis_graph()


async def run_analysis(ticker: str, closes: List[float], volumes: List[int]) -> dict:
    """
    Entry point: run the full analysis graph for one ticker.
    Returns the final state dict.
    """
    initial_state = AnalysisState(
        ticker=ticker,
        closes=closes,
        volumes=volumes,
        session_id=str(uuid.uuid4()),
        stats_result=None,
        llm_result=None,
        signal_id=None,
        error=None,
    )
    final_state = await analysis_graph.ainvoke(initial_state)
    return final_state
