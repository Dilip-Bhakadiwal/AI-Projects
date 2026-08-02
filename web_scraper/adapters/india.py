"""
adapters/india.py — India-specific Adapter (Stage 4d).

Handles Indian equities (NSE/BSE) that Yahoo Finance doesn't cover well.
Uses multiple data sources:
  1. Yahoo Finance chart endpoint with both .NS and .BO suffixes
  2. Screener.in search → company page scrape for key metrics

Returns an AdapterResult.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Optional

import requests

from schema import AdapterResult

logger = logging.getLogger(__name__)

SOURCE = "india"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

# Yahoo Finance chart endpoint (try both suffixes)
YF_CHART_URL = "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"

# Screener.in endpoints (no auth needed)
SCREENER_SEARCH = "https://www.screener.in/api/company/search/?q={query}&fields=name,ticker"
SCREENER_COMPANY = "https://www.screener.in/company/{ticker}/consolidated/"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_float(value) -> Optional[float]:
    try:
        if value is None:
            return None
        s = str(value).replace(",", "").replace("%", "").strip()
        v = float(s)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def _safe_int(value) -> Optional[int]:
    try:
        if value is None:
            return None
        s = str(value).replace(",", "").strip()
        return int(float(s))
    except (TypeError, ValueError):
        return None


def _strip_exchange_suffix(symbol: str) -> str:
    """ZOMATO.NS → ZOMATO, COLPAL.BO → COLPAL"""
    return re.sub(r"\.(NS|BO|NSE|BSE)$", "", symbol.upper())


def _try_yahoo_chart(symbol: str) -> Optional[dict]:
    """Try to fetch data from Yahoo Finance chart endpoint for Indian stocks."""
    base = _strip_exchange_suffix(symbol)
    # Try NSE first, then BSE
    for suffix in [".NS", ".BO"]:
        url = YF_CHART_URL.format(symbol=base + suffix)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=8)
            if resp.ok:
                data = resp.json()
                result = data.get("chart", {}).get("result") or []
                if result:
                    meta = result[0]["meta"]
                    price = meta.get("regularMarketPrice")
                    if price and float(price) > 0:
                        logger.debug("Yahoo chart succeeded for %s%s", base, suffix)
                        return meta
        except Exception as exc:
            logger.debug("Yahoo chart failed for %s%s: %s", base, suffix, exc)
    return None


def _screener_lookup(query: str) -> Optional[dict]:
    """
    Look up a company on Screener.in and return basic data scraped from their page.
    Returns dict with company name and ticker, or None on failure.
    """
    clean = _strip_exchange_suffix(query)
    url = SCREENER_SEARCH.format(query=requests.utils.quote(clean))
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if not resp.ok:
            return None
        results = resp.json()
        if not results:
            return None
        # Return the first match
        return results[0]
    except Exception as exc:
        logger.debug("Screener search failed for %r: %s", query, exc)
        return None


def _parse_screener_value(text: str) -> Optional[float]:
    """Parse values like '₹302.45', '25.3%', '1,234.56 Cr' etc."""
    if not text:
        return None
    # Remove currency symbols, commas
    cleaned = re.sub(r"[₹$,\s]", "", text)
    # Handle Cr (crores) and B (billions)
    multiplier = 1.0
    if cleaned.endswith("Cr"):
        cleaned = cleaned[:-2]
        multiplier = 1e7   # crores → rupees
    elif cleaned.endswith("B") or cleaned.endswith("b"):
        cleaned = cleaned[:-1]
        multiplier = 1e9
    # Remove trailing % or other chars
    cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
    try:
        return float(cleaned) * multiplier
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Public fetch function
# ---------------------------------------------------------------------------

def fetch(symbol: str) -> AdapterResult:
    """
    Fetch Indian stock data.
    Tries Yahoo chart endpoint first; falls back to Screener.in name lookup.

    Args:
        symbol: Exchange-qualified symbol, e.g. "ZOMATO.NS" or "ETERNAL.NS"

    Returns:
        AdapterResult
    """
    now = datetime.now(timezone.utc)
    base = _strip_exchange_suffix(symbol)

    # ---- Attempt 1: Yahoo chart (catches most NSE stocks) ----
    meta = _try_yahoo_chart(symbol)
    if meta:
        price      = _safe_float(meta.get("regularMarketPrice") or meta.get("previousClose"))
        change     = _safe_float(meta.get("regularMarketChange"))
        pct_change = _safe_float(meta.get("regularMarketChangePercent"))
        volume     = _safe_int(meta.get("regularMarketVolume"))
        name       = meta.get("longName") or meta.get("shortName") or base

        if price and price > 0:
            return AdapterResult(
                ticker=symbol,
                name=name,
                last_price=price,
                change=change,
                pct_change=pct_change,
                volume=volume,
                market_cap=None,
                pe_ratio=None,
                div_yield=None,
                source=f"{SOURCE}_yahoo",
                fetched_at=now,
                success=True,
            )

    # ---- Attempt 2: Screener.in lookup for company name/ticker ----
    screener_result = _screener_lookup(base)
    if screener_result:
        # Screener returned the actual NSE ticker; try Yahoo with that
        actual_ticker = screener_result.get("ticker", base)
        logger.info(
            "Screener mapped %r → ticker %r (%s)",
            base,
            actual_ticker,
            screener_result.get("name", ""),
        )
        if actual_ticker != base:
            meta = _try_yahoo_chart(actual_ticker + ".NS")
            if meta:
                price      = _safe_float(meta.get("regularMarketPrice") or meta.get("previousClose"))
                change     = _safe_float(meta.get("regularMarketChange"))
                pct_change = _safe_float(meta.get("regularMarketChangePercent"))
                volume     = _safe_int(meta.get("regularMarketVolume"))
                name       = (
                    meta.get("longName")
                    or meta.get("shortName")
                    or screener_result.get("name", actual_ticker)
                )
                if price and price > 0:
                    return AdapterResult(
                        ticker=f"{actual_ticker}.NS",
                        name=name,
                        last_price=price,
                        change=change,
                        pct_change=pct_change,
                        volume=volume,
                        market_cap=None,
                        pe_ratio=None,
                        div_yield=None,
                        source=f"{SOURCE}_screener",
                        fetched_at=now,
                        success=True,
                    )

    return AdapterResult(
        ticker=symbol,
        source=SOURCE,
        fetched_at=now,
        success=False,
        error=f"India adapter: could not find data for {symbol}",
    )
