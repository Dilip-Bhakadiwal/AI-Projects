"""
app/services/stock_scraper.py — Integration bridge for 'web_scraper' (7-Stage Pipeline).

Connects MarketPulse to the modular stock scraper located at '../web_scraper'.
Provides synchronous and asynchronous helpers to resolve queries (e.g. 'zomato', 'swiggy', 'AAPL')
and return normalized financial data dictionaries compatible with MarketPulse models and tools.
"""
from __future__ import annotations

import os
import sys
import asyncio
import structlog
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = structlog.get_logger(__name__)

# Ensure 'web_scraper' is available on sys.path
_SCRAPER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../web_scraper"))
if _SCRAPER_DIR not in sys.path:
    sys.path.insert(0, _SCRAPER_DIR)

try:
    from scraper import fetch_stock as _fetch_stock_sync
    from resolver import resolve as _resolve_sync
except ImportError as exc:
    _fetch_stock_sync = None
    _resolve_sync = None
    logger.warning("web_scraper_import_failed", error=str(exc), path=_SCRAPER_DIR)


def _determine_currency(exchange: str, symbol: str) -> str:
    """Infer trading currency from exchange or ticker suffix."""
    ex = (exchange or "").upper()
    sym = (symbol or "").upper()
    if ex in ("NSE", "BSE", "NSI", "BO", "INR") or sym.endswith(".NS") or sym.endswith(".BO") or sym.endswith(".IN"):
        return "INR"
    if sym.endswith(".KS"):
        return "KRW"
    if sym.endswith(".SS") or sym.endswith(".SZ") or ex in ("SHH", "SHZ"):
        return "CNY"
    if sym.endswith(".L") or ex == "LSE":
        return "GBP"
    if sym.endswith(".PA") or sym.endswith(".DE") or sym.endswith(".MI"):
        return "EUR"
    return "USD"


FX_RATES_TO_USD = {
    "USD": 1.0,
    "INR": 83.50,
    "EUR": 0.92,
    "GBP": 0.79,
    "KRW": 1380.0,
    "CNY": 7.25,
    "JPY": 155.0,
    "CAD": 1.37,
    "AUD": 1.52,
    "HKD": 7.80,
}


def normalize_snapshot_to_usd(snapshot: dict) -> dict:
    """
    Automatically converts any foreign currency stock price and valuation fields into USD ($).
    Percentage fields (change_pct, pe_ratio, dividend_yield) and counts (volume) remain invariant.
    """
    if not snapshot:
        return snapshot
    curr = str(snapshot.get("currency") or "USD").upper()
    if curr == "USD":
        return snapshot

    rate = FX_RATES_TO_USD.get(curr, 1.0)
    if rate <= 0 or rate == 1.0:
        snapshot["currency"] = "USD"
        return snapshot

    for field in ("last_price", "change_val", "open_price", "previous_close", "day_high", "day_low", "high_52week", "low_52week"):
        val = snapshot.get(field)
        if val is not None and isinstance(val, (int, float)) and val != 0:
            snapshot[field] = round(float(val) / rate, 2)

    for field in ("eps",):
        val = snapshot.get(field)
        if val is not None and isinstance(val, (int, float)) and val != 0:
            snapshot[field] = round(float(val) / rate, 4)

    for field in ("market_cap",):
        val = snapshot.get(field)
        if val is not None and isinstance(val, (int, float)) and val != 0:
            snapshot[field] = int(float(val) / rate)

    snapshot["currency"] = "USD"
    logger.info("normalized_currency_to_usd", ticker=snapshot.get("ticker"), original_currency=curr, rate=rate)
    return snapshot


COMMON_SYMBOL_ALIASES = {
    "OLA": "OLAELEC.NS",
    "OLA ELECTRIC": "OLAELEC.NS",
    "OLAELEC": "OLAELEC.NS",
    "OLAC": "OLAELEC.NS",
    "OLAC.NS": "OLAELEC.NS",
    "OLA.CA": "OLAELEC.NS",
    "ADANI": "ADANIENT.NS",
    "ADANI ENTERPRISES": "ADANIENT.NS",
    "ZOMATO": "ZOMATO.NS",
    "SWIGGY": "SWIGGY.NS",
    "BLUESTONE": "BLUESTONE.NS",
    "ETERNAL": "ETERNAL.NS",
}


def _resolve_symbol_alias(query: str) -> str:
    clean_query = query.strip()
    clean_upper = clean_query.upper()
    for alias, canonical in COMMON_SYMBOL_ALIASES.items():
        if clean_upper == alias or clean_upper.replace(".", "").replace(" ", "") == alias.replace(" ", ""):
            logger.info("mapped_symbol_alias", original=query, canonical=canonical)
            return canonical
    return clean_query


def get_stock_snapshot_sync(query: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """
    Synchronously fetch stock data using the 7-stage web_scraper pipeline.
    Returns a dictionary formatted for MarketPulse DB schema and agents, or None on failure.
    """
    if _fetch_stock_sync is None:
        logger.error("scraper_not_available", query=query)
        return None

    clean_query = _resolve_symbol_alias(query)
    logger.info("stock_scraper_fetching", query=clean_query, force_refresh=force_refresh)

    try:
        result = _fetch_stock_sync(clean_query, force_refresh=force_refresh)
    except Exception as exc:
        logger.error("stock_scraper_error", query=clean_query, error=str(exc))
        return None

    if not result or "error" in result:
        logger.warning("stock_scraper_failed", query=clean_query, error=result.get("error") if result else "None")
        return None

    ticker = result.get("ticker", clean_query.upper())
    raw_name = result.get("name") or ticker
    if clean_query.upper() != ticker.upper() and clean_query.upper() not in raw_name.upper():
        company_name = f"{raw_name} ({clean_query.title()})"
    else:
        company_name = raw_name

    last_price = float(result.get("last_price") or 0.0)
    change_val = float(result.get("change") or 0.0)
    change_pct = float(result.get("pct_change") or 0.0)
    previous_close = round(last_price - change_val, 4) if last_price > 0 and "change" in result else last_price
    exchange = result.get("resolved_exchange") or ""
    currency = _determine_currency(exchange, ticker)

    snapshot = {
        "ticker": ticker,
        "company_name": company_name,
        "last_price": last_price,
        "change_val": change_val,
        "change_pct": change_pct,
        "volume": int(result["volume"]) if result.get("volume") else None,
        "open_price": float(result["open"]) if result.get("open") else None,
        "previous_close": previous_close,
        "day_high": float(result["high"]) if result.get("high") else None,
        "day_low": float(result["low"]) if result.get("low") else None,
        "market_cap": int(result["market_cap"]) if result.get("market_cap") else None,
        "currency": currency,
        "pe_ratio": float(result["pe_ratio"]) if result.get("pe_ratio") and float(result["pe_ratio"]) > 0 else None,
        "high_52week": float(result["high_52week"]) if result.get("high_52week") else None,
        "low_52week": float(result["low_52week"]) if result.get("low_52week") else None,
        "dividend_yield": float(result["div_yield"]) if result.get("div_yield") and float(result["div_yield"]) > 0 else None,
        "eps": float(result["eps"]) if result.get("eps") and float(result["eps"]) > 0 else None,
        "exchange": exchange or "DEFAULT",
        "last_updated": datetime.now(timezone.utc),
    }
    snapshot = normalize_snapshot_to_usd(snapshot)
    logger.info("stock_scraper_success", ticker=ticker, price=snapshot["last_price"], currency=snapshot["currency"], source=result.get("source", ""))
    return snapshot


async def get_stock_snapshot(query: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """
    Asynchronously fetch stock data using the 7-stage web_scraper pipeline.
    Runs the synchronous pipeline in a background thread to prevent blocking asyncio loop.
    """
    return await asyncio.to_thread(get_stock_snapshot_sync, query, force_refresh)
