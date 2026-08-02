"""
app/agents/query_agent/tools/db_read.py
Database Read Tools for single-table architecture.
"""
import structlog
from langchain_core.tools import tool
from sqlalchemy import select, text

from app.database import AsyncSessionLocal
from app.models.stock import Stock

logger = structlog.get_logger(__name__)


@tool(response_format="content_and_artifact")
async def view_portfolio_table() -> tuple[str, str]:
    """
    List ALL stocks currently tracked in the database and their snapshots.
    Use this when the user asks 'what is in the database?', 'show me the table', or 'what stocks do you track?'.
    Returns a formatted Markdown table of the stock portfolio.
    """
    logger.info("tool_view_portfolio_table")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Stock))
        stocks = result.scalars().all()
        
    if not stocks:
        return "No stocks tracked yet. Use add_stock to add one.", ""

    md_table = "| Ticker | Name | Last Price | Change | % Change | Volume | Market Cap | P/E | Div Yld |\n"
    md_table += "|---|---|---|---|---|---|---|---|---|\n"
    
    for s in stocks:
        md_table += f"| {s.ticker} | {s.company_name} | {s.last_price} | {s.change_val:+.2f} | {s.change_pct:+.2f}% | {s.volume} | {s.market_cap} | {s.pe_ratio} | {s.dividend_yield}% |\n"
        
    return f"TABLE_DISPLAYED: {len(stocks)} stocks. Your response MUST be exactly: 'Here is the stock portfolio:' followed by nothing else.", md_table


@tool(response_format="content_and_artifact")
async def query_database(sql_query: str) -> tuple[str, str]:
    """
    Execute a read-only SQL SELECT query on the PostgreSQL database.
    Use this to answer data questions: highest price, average volume, sort by market cap, filter by exchange, etc.
    The ONLY table is: stocks
    Columns: ticker, company_name, last_price, change_val, change_pct, volume, open_price, previous_close,
             day_high, day_low, market_cap, currency, pe_ratio, high_52week, low_52week, dividend_yield, eps, exchange, last_updated
    IMPORTANT: Only SELECT queries. Never UPDATE, INSERT, or DELETE.
    """
    logger.info("tool_query_database", query=sql_query)

    try:
        from app.services.sql_guard import validate_and_sanitize_sql, SecurityGuardrailException
        safe_query = validate_and_sanitize_sql(sql_query)
    except Exception as guard_exc:
        logger.warning("tool_query_database_guardrail_blocked", query=sql_query, error=str(guard_exc))
        return f"SECURITY GUARDRAIL ERROR: {str(guard_exc)} Only read-only SELECT statements are permitted.", ""

    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text("SET TRANSACTION READ ONLY;"))
            result = await session.execute(text(safe_query))
            rows = result.mappings().all()

            if not rows:
                return "QUERY_DISPLAYED: Query returned no results.", "*(No rows returned)*"

            row_count = len(rows)
            summary_items = []
            for r in rows[:10]:
                summary_items.append(", ".join(f"{k}: {v}" for k, v in r.items() if v is not None))
            data_summary = "; ".join(summary_items)

            if row_count == 1:
                return (
                    f"Query executed successfully (1 row): {data_summary}. INSTRUCTION: Provide a smart, direct, conversational ONE-LINE answer stating the exact result (e.g. ticker, company name, price, or metric). STRICT CURRENCY RULE: All database prices are in USD ($). NEVER use foreign currency symbols like ₹ or €. Do NOT say 'Here are the results:'.",
                    ""
                )
            else:
                headers = list(rows[0].keys())
                md = "| " + " | ".join(str(h).replace("_", " ").title() for h in headers) + " |\n"
                md += "| " + " | ".join(["---"] * len(headers)) + " |\n"
                for row in rows:
                    md += "| " + " | ".join(str(v) if v is not None else "—" for v in row.values()) + " |\n"
                return (
                    f"Query executed successfully ({row_count} rows): {data_summary}. INSTRUCTION: Provide a smart, concise conversational summary of the top result or insight from this data. STRICT CURRENCY RULE: All database prices are in USD ($). NEVER use foreign currency symbols like ₹ or €. Do NOT say 'Here are the results:'.",
                    md
                )
        except Exception as e:
            err = str(e).split("\n")[0]
            return f"SQL Error: {err}", ""
