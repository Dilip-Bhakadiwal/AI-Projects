"""
app/agents/query_agent/tools/db_write.py
Database Write Tools for single-table architecture.

Design principle: ALL fallback logic lives INSIDE the tool, not in the LLM's
reasoning chain. Weak LLMs cannot reliably orchestrate 3+ sequential tool calls.
"""
import re
import json
import structlog
import asyncio
import yfinance as yf
from datetime import datetime, timezone
from langchain_core.tools import tool
from ddgs import DDGS

from app.database import AsyncSessionLocal
from app.models.stock import Stock

logger = structlog.get_logger(__name__)


def _extract_price_from_text(text: str) -> float | None:
    """
    Extract a realistic stock price from a web search snippet.
    Prioritizes numbers near currency symbols and applies a sanity range.
    """
    # Priority: look for number immediately following a currency symbol
    currency_patterns = [
        r'₹\s*([\d,]+(?:\.\d{1,2})?)',     # Indian Rupee
        r'\$\s*([\d,]+(?:\.\d{1,2})?)',     # US Dollar
        r'Rs\.?\s*([\d,]+(?:\.\d{1,2})?)',  # Rs abbreviation
    ]
    for pat in currency_patterns:
        for match in re.finditer(pat, text):
            try:
                val = float(match.group(1).replace(',', ''))
                if 0.01 < val < 100_000:   # realistic single-stock price
                    return val
            except ValueError:
                continue

    # Fallback: look for "price is X" or "trading at X" patterns
    contextual = [
        r'(?:price|trading|closed|last)\s+(?:at|is|of|@)?\s*(?:₹|\$|Rs\.?)?\s*([\d,]+(?:\.\d{1,2})?)',
    ]
    for pat in contextual:
        for match in re.finditer(pat, text, re.IGNORECASE):
            try:
                val = float(match.group(1).replace(',', ''))
                if 0.01 < val < 100_000:
                    return val
            except ValueError:
                continue
    return None


async def _upsert_stock(data: dict) -> str:
    """Write a stock dict to the DB (insert or update)."""
    data = dict(data)
    ticker = data.pop("ticker")
    async with AsyncSessionLocal() as session:
        existing = await session.get(Stock, ticker)
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            await session.commit()
            return f"Updated {ticker} in the database."
        else:
            new_stock = Stock(ticker=ticker, **data)
            session.add(new_stock)
            await session.commit()
            return f"Added {ticker} in the database."


@tool
async def add_stock(ticker: str) -> str:
    """
    Add a new stock to the tracking database.
    Tries Yahoo Finance first. If not found, automatically searches the web
    to find the current price and inserts it anyway.
    Use this for ALL 'add', 'track', or 'watch' requests.
    The fallback is fully automatic — you never need to call add_custom_stock manually.
    """
    ticker = ticker.upper().strip()
    logger.info("tool_add_stock", ticker=ticker)

    def _sf(val, default=0.0):
        try: return float(val) if val is not None else default
        except: return default

    # ── STAGE 1: Try web_scraper 7-stage pipeline (multi-source + auto-resolve) ──
    try:
        from app.services.stock_scraper import get_stock_snapshot
        snapshot = await get_stock_snapshot(ticker)
        if snapshot and snapshot.get("last_price", 0.0) > 0:
            result = await _upsert_stock(snapshot)
            logger.info("tool_add_stock_scraper_ok", ticker=snapshot["ticker"])
            return result
    except Exception as e:
        logger.warning("tool_add_stock_scraper_failed", ticker=ticker, error=str(e))

    # ── STAGE 2: Automatic web search fallback ───────────────────────────
    logger.info("tool_add_stock_web_fallback", ticker=ticker)
    try:
        query = f"{ticker} stock price current"
        raw_results = await asyncio.to_thread(lambda: list(DDGS().text(query, max_results=5)))

        price = None
        company_name = ticker
        currency = "USD"

        for r in raw_results:
            snippet = r.get("body", "") + " " + r.get("title", "")

            # Try to detect currency
            if "₹" in snippet or "INR" in snippet or "NSE" in snippet or "BSE" in snippet:
                currency = "INR"
            elif "GBP" in snippet or "£" in snippet:
                currency = "GBP"

            # Try to extract a company name from title
            title = r.get("title", "")
            if "share price" in title.lower() or "stock price" in title.lower():
                name_part = title.split("-")[0].strip()
                if name_part and len(name_part) < 60:
                    company_name = name_part

            # Try to extract price
            if price is None:
                price = _extract_price_from_text(snippet)

        if price is None:
            return f"Could not add {ticker}. Yahoo Finance has no data and the web search returned no clear price. Please verify the ticker symbol."

        stock_data = {
            "ticker": ticker,
            "company_name": company_name,
            "last_price": price, "change_val": 0.0, "change_pct": 0.0,
            "volume": 0, "open_price": price, "previous_close": price,
            "day_high": price, "day_low": price, "market_cap": 0,
            "currency": currency, "pe_ratio": 0.0,
            "high_52week": price, "low_52week": price,
            "dividend_yield": 0.0, "eps": 0.0, "exchange": "WEB",
            "last_updated": datetime.now(timezone.utc)
        }
        result = await _upsert_stock(stock_data)
        logger.info("tool_add_stock_web_ok", ticker=ticker, price=price, currency=currency)
        return f"{result} (price {price} {currency} sourced from web — Yahoo Finance had no data)"

    except Exception as e:
        logger.error("tool_add_stock_web_fallback_failed", ticker=ticker, error=str(e))
        return f"Could not add {ticker}. Both Yahoo Finance and web search failed. Error: {str(e)}"


@tool
async def remove_stock(ticker: str) -> str:
    """
    Remove a stock from the tracking database.
    Use this when the user asks to 'delete', 'remove', or 'stop tracking' a stock.
    """
    ticker = ticker.upper().strip()
    logger.info("tool_remove_stock", ticker=ticker)

    async with AsyncSessionLocal() as session:
        stock = await session.get(Stock, ticker)
        if not stock:
            return f"Stock {ticker} is not currently tracked."
            
        await session.delete(stock)
        await session.commit()
        return f"Successfully removed {ticker} from the database."


@tool
async def refresh_stock(ticker: str) -> str:
    """
    Refresh/update an existing stock's price and all values in the database.
    Use this when the user says 'update ZOMATO', 'refresh AMD', 'get latest data for AAPL'.
    Fetches fresh data from Yahoo Finance (or web if needed) and overwrites the current values.
    """
    ticker = ticker.upper().strip()
    logger.info("tool_refresh_stock", ticker=ticker)
    # Reuse add_stock logic — it upserts, so it always updates if the row exists
    result = await add_stock.ainvoke({"ticker": ticker})
    return f"Refreshed {ticker}: {result}"


@tool
async def refresh_all_stocks() -> str:
    """
    Refresh ALL stocks in the database with the latest prices and values in USD ($).
    Use this when the user says 'update the table', 'update database', 'refresh stock prices', 'update all', 'sync database', 'get latest values'.
    Fetches fresh data for every tracked ticker, converts all currencies to USD ($), and updates the database.
    """
    logger.info("tool_refresh_all_stocks")
    from app.services.stock_scraper import FX_RATES_TO_USD
    async with AsyncSessionLocal() as session:
        result = await session.execute(__import__('sqlalchemy').select(Stock))
        all_stocks = result.scalars().all()
        tickers = [s.ticker for s in all_stocks]

    if not tickers:
        return "No stocks in the database to refresh."

    summary_lines = [f"Refreshing and normalizing {len(tickers)} stocks to USD ($)..."]
    ok, failed = 0, 0

    for ticker in tickers:
        try:
            res = await add_stock.ainvoke({"ticker": ticker})
            summary_lines.append(f"  OK  {ticker:12} → updated to USD ($)")
            ok += 1
        except Exception as e:
            # Fallback: convert existing DB row from foreign currency to USD using FX rates
            try:
                async with AsyncSessionLocal() as session:
                    st = await session.get(Stock, ticker)
                    if st and st.currency and st.currency.upper() != "USD":
                        rate = FX_RATES_TO_USD.get(st.currency.upper(), 1.0)
                        if rate > 0 and rate != 1.0:
                            if st.last_price: st.last_price = round(st.last_price / rate, 2)
                            if st.change_val: st.change_val = round(st.change_val / rate, 2)
                            if st.open_price: st.open_price = round(st.open_price / rate, 2)
                            if st.previous_close: st.previous_close = round(st.previous_close / rate, 2)
                            if st.day_high: st.day_high = round(st.day_high / rate, 2)
                            if st.day_low: st.day_low = round(st.day_low / rate, 2)
                            if st.high_52week: st.high_52week = round(st.high_52week / rate, 2)
                            if st.low_52week: st.low_52week = round(st.low_52week / rate, 2)
                            if st.market_cap: st.market_cap = int(st.market_cap / rate)
                            st.currency = "USD"
                            await session.commit()
                summary_lines.append(f"  OK  {ticker:12} → normalized to USD ($) via FX rate")
                ok += 1
            except Exception as e2:
                summary_lines.append(f"  ERR {ticker:12} → {str(e2)[:40]}")
                failed += 1

    summary_lines.append(f"\nDone: {ok} stocks updated and normalized to USD ($).")
    return "\n".join(summary_lines)


@tool
async def add_custom_stock(ticker: str, company_name: str, last_price: float, currency: str = "USD") -> str:
    """
    Use this ONLY if add_stock fails! 
    Inserts web-scraped data into the database when Yahoo Finance has no data.
    """
    ticker = ticker.upper().strip()
    logger.info("tool_add_custom_stock", ticker=ticker)

    stock_data = {
        "ticker": ticker,
        "company_name": company_name,
        "last_price": last_price,
        "change_val": 0.0,
        "change_pct": 0.0,
        "volume": 0,
        "open_price": last_price,
        "previous_close": last_price,
        "day_high": last_price,
        "day_low": last_price,
        "market_cap": 0,
        "currency": currency,
        "pe_ratio": 0.0,
        "high_52week": last_price,
        "low_52week": last_price,
        "dividend_yield": 0.0,
        "eps": 0.0,
        "exchange": "CUSTOM",
        "last_updated": datetime.now(timezone.utc)
    }

    try:
        async with AsyncSessionLocal() as session:
            existing = await session.get(Stock, ticker)
            if existing:
                for k, v in stock_data.items():
                    setattr(existing, k, v)
                await session.commit()
                return f"Successfully updated custom stock {ticker} in the database."
            else:
                new_stock = Stock(**stock_data)
                session.add(new_stock)
                await session.commit()
                return f"Successfully added custom stock {ticker} to the database using web-scraped data."
    except Exception as e:
        logger.error("tool_add_custom_stock_failed", ticker=ticker, error=str(e))
        return f"Failed to add custom stock {ticker}. Error: {str(e)}"
