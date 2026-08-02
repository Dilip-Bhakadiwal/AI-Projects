"""
Financial Data Tools
"""
import json
import structlog
import yfinance as yf
from langchain_core.tools import tool

logger = structlog.get_logger(__name__)


def _build_result_text(ticker: str, resolved: str, name: str, price: float,
                       prev: float | None, change_val: float | None,
                       change_pct: float | None, currency: str, snapshot: dict | None,
                       include_widget: bool) -> tuple[str, dict]:
    """Build the tool return tuple from price data."""
    diff = change_val if change_val is not None else (round(price - prev, 4) if prev else 0.0)
    pct  = change_pct if change_pct is not None else (round(diff / prev * 100, 4) if prev else 0.0)

    widget_json = {
        "ticker": resolved,
        "name": name,
        "price": f"{price:,.2f}",
        "currency": currency,
        "change_pct": f"{pct:+.2f}%",
        "change_val": f"{diff:+.2f}",
        "open":    str((snapshot or {}).get("open_price")  or "N/A"),
        "high":    str((snapshot or {}).get("day_high")    or "N/A"),
        "low":     str((snapshot or {}).get("day_low")     or "N/A"),
        "mkt_cap": str((snapshot or {}).get("market_cap") or "N/A"),
        "pe":      str((snapshot or {}).get("pe_ratio")   or "N/A"),
        "div":     (f"{(snapshot or {}).get('dividend_yield', 0):.2f}%"
                    if (snapshot or {}).get("dividend_yield") else "N/A"),
        "high_52": str((snapshot or {}).get("high_52week") or "N/A"),
        "low_52":  str((snapshot or {}).get("low_52week")  or "N/A"),
    }

    summary = (
        f"Live stock data for '{ticker}' (Symbol: {resolved} | Company: {name}):\n"
        f"- Current Price: {price:,.2f} {currency}\n"
        f"- Change: {diff:+.2f} ({pct:+.2f}%)\n"
        f"- Exchange: {(snapshot or {}).get('exchange', 'N/A')}\n"
        f"- Market Cap: {(snapshot or {}).get('market_cap', 'N/A')}\n"
        f"- P/E Ratio: {(snapshot or {}).get('pe_ratio', 'N/A')}\n\n"
        f"(Agent Instruction: The stock price for '{ticker}' is {price:,.2f} {currency} "
        f"under ticker symbol {resolved}. Answer the user directly with this price.)"
    )

    if include_widget:
        widget_summary = (
            f"Live stock data for '{ticker}' (Symbol: {resolved} | Company: {name}):\n"
            f"- Current Price: {price:,.2f} {currency}\n"
            f"- Change: {diff:+.2f} ({pct:+.2f}%)\n"
            f"Successfully displayed widget to user.\n\n"
            f"(Agent Instruction: The stock price for '{ticker}' is {price:,.2f} {currency}. "
            f"Answer the user directly with this price.)"
        )
        return widget_summary, widget_json

    return summary, {}


@tool(response_format="content_and_artifact")
def get_financial_data(ticker: str, include_widget: bool = False) -> tuple[str, dict]:
    """
    Get live financial data, fundamentals, and recent quotes for any stock (including Indian NSE/BSE and US stocks).
    Use this when the user asks for the current price, market cap, P/E ratio, or live stock information.
    Args:
        ticker: The stock symbol or company name (e.g., 'AAPL', 'ZOMATO', 'SWIGGY', 'COLPAL.NS', '005930.KS')
        include_widget: MUST be True when user says 'show card', 'show widget', 'show chart', 'full report', or 'show me a card for X'. Defaults to False for simple price questions.
    """
    logger.info("tool_get_financial_data", ticker=ticker, widget_requested=include_widget)
    symbol = ticker.strip().upper()

    # ── Path 1: Full 7-stage web scraper pipeline (works locally) ──────────
    try:
        from app.services.stock_scraper import get_stock_snapshot_sync
        snapshot = get_stock_snapshot_sync(symbol)
        if snapshot and snapshot.get("last_price", 0.0) > 0:
            return _build_result_text(
                ticker=ticker,
                resolved=snapshot["ticker"],
                name=snapshot.get("company_name", symbol),
                price=snapshot["last_price"],
                prev=snapshot.get("previous_close"),
                change_val=snapshot.get("change_val"),
                change_pct=snapshot.get("change_pct"),
                currency=snapshot.get("currency", "USD"),
                snapshot=snapshot,
                include_widget=include_widget,
            )
        logger.warning("scraper_returned_zero", ticker=symbol)
    except Exception as e:
        logger.warning("scraper_pipeline_failed", ticker=symbol, error=str(e))

    # ── Path 2: Direct yfinance (fast_info) ────────────────────────────────
    try:
        fi = yf.Ticker(symbol).fast_info
        price = getattr(fi, "last_price", None)
        if price and float(price) > 0:
            prev = getattr(fi, "previous_close", None)
            diff = round(float(price) - float(prev), 4) if prev else 0.0
            pct  = round(diff / float(prev) * 100, 4) if prev else 0.0
            logger.info("yfinance_fast_info_success", ticker=symbol, price=price)
            return _build_result_text(
                ticker=ticker, resolved=symbol, name=symbol,
                price=float(price), prev=float(prev) if prev else None,
                change_val=diff, change_pct=pct,
                currency=getattr(fi, "currency", "USD") or "USD",
                snapshot=None, include_widget=include_widget,
            )
    except Exception as e:
        logger.warning("yfinance_fast_info_failed", ticker=symbol, error=str(e))

    # ── Path 3: Cloud-friendly direct REST fallback (Render-safe) ──────────
    try:
        from app.services.price_fallback import fetch_price_cloud
        fb = fetch_price_cloud(symbol)
        if fb and fb.get("price", 0.0) > 0:
            logger.info("price_fallback_used", ticker=symbol, source=fb.get("source"))
            return _build_result_text(
                ticker=ticker, resolved=symbol,
                name=fb.get("name", symbol),
                price=float(fb["price"]),
                prev=fb.get("prev_close"),
                change_val=fb.get("change_val"),
                change_pct=fb.get("change_pct"),
                currency=fb.get("currency", "USD"),
                snapshot={
                    "exchange": fb.get("exchange", ""),
                    "open_price": fb.get("open_price"),
                    "day_high": fb.get("day_high"),
                    "day_low": fb.get("day_low"),
                    "market_cap": fb.get("market_cap"),
                    "pe_ratio": fb.get("pe_ratio"),
                    "high_52week": None,
                    "low_52week": None,
                    "dividend_yield": None,
                },
                include_widget=include_widget,
            )
    except Exception as e:
        logger.warning("price_fallback_failed", ticker=symbol, error=str(e))

    # ── All paths failed ───────────────────────────────────────────────────
    return (
        f"TOOL_FAILURE: Could not retrieve live stock data for '{ticker}' from any source. "
        f"INSTRUCTION: Do NOT call get_financial_data again. Answer the user directly explaining "
        f"that '{ticker}' market data is temporarily unavailable, and suggest they check "
        f"Yahoo Finance (https://finance.yahoo.com/quote/{symbol}/) directly.",
        {}
    )
