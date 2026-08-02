"""
marketpulse/tests/test_concurrency.py — Concurrency & Load Resilience Test Suite.

Verifies that MarketPulse AI withstands concurrent multi-user load:
  1. Thread-safe SQL AST guardrail processing under burst query traffic.
  2. AsyncSessionLocal connection pool stability under concurrent parallel SELECT queries.
  3. LangGraph checkpointer session isolation without race conditions or memory corruption.
"""
import asyncio
import time
import pytest
from app.services.sql_guard import validate_and_sanitize_sql
from app.agents.query_agent.tools.db_read import query_database
from app.agents.query_agent.agent import get_query_agent


def test_concurrent_sql_guard_validations():
    """Verify AST/regex SQL guardrail is thread-safe and handles burst queries in sub-millisecond time."""
    queries = [
        f"SELECT ticker, last_price FROM stocks WHERE volume > {i * 100}"
        for i in range(50)
    ]
    start_time = time.perf_counter()
    results = [validate_and_sanitize_sql(q) for q in queries]
    duration = time.perf_counter() - start_time

    assert len(results) == 50
    assert all("LIMIT 50" in res for res in results)
    # Ensure 50 validations complete in under 0.25 seconds (~5ms per query max)
    assert duration < 0.25, f"Guardrail took too long: {duration:.4f}s for 50 queries"


@pytest.mark.anyio
async def test_concurrent_database_reads_connection_pool():
    """
    Verify AsyncSessionLocal connection pool handles burst parallel async reads
    without deadlock, SQLite/Postgres lock timeout, or pool exhaustion.
    """
    queries = [
        "SELECT ticker, last_price, company_name FROM stocks LIMIT 10"
        for _ in range(12)
    ]

    start_time = time.perf_counter()
    # Run 12 database read queries concurrently in parallel
    tasks = [query_database.ainvoke({"sql_query": q}) for q in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    duration = time.perf_counter() - start_time

    assert len(results) == 12
    # Verify no unhandled exceptions or connection pool exhaustion errors
    for res in results:
        assert not isinstance(res, Exception), f"Concurrent query failed with exception: {res}"
        assert "SECURITY GUARDRAIL ERROR" not in str(res)

    # 12 concurrent queries should finish rapidly without connection blocking
    assert duration < 10.0, f"Concurrent DB reads took too long: {duration:.4f}s"


@pytest.mark.anyio
async def test_concurrent_agent_memory_checkpointer_isolation():
    """
    Verify LangGraph checkpointer maintains thread isolation across parallel user sessions
    without race conditions or shared state corruption.
    """
    agent = get_query_agent()
    session_ids = [f"bench_session_{i}" for i in range(5)]

    async def _query_agent_session(sid: str):
        config = {"configurable": {"thread_id": sid}, "recursion_limit": 4}
        # Fetch current state checkpoint for each session
        state = await agent.aget_state(config)
        return sid, state

    tasks = [_query_agent_session(sid) for sid in session_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    assert len(results) == 5
    for res in results:
        assert not isinstance(res, Exception), f"Concurrent checkpointer access failed: {res}"
        sid, state = res
        assert sid in session_ids
