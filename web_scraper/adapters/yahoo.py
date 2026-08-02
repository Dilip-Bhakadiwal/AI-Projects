"""
adapters/yahoo.py — Yahoo Finance Adapter (Stage 4a).

Uses the yfinance library with a direct fallback to Yahoo's quote summary
endpoint for reliability.  Returns an AdapterResult.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

import requests
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from schema import AdapterResult

logger = logging.getLogger(__name__)

SOURCE = "yahoo"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_float(value) -> Optional[float]:
    try:
        v = float(value)
        return v if v == v else None   # filter NaN
    except (TypeError, ValueError):
        return None


def _safe_int(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# yfinance fetch (primary path)
# ---------------------------------------------------------------------------

@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    reraise=True,
)
def _fetch_via_yfinance(symbol: str) -> dict:
    """Fetch stock info dict from yfinance — try fast_info then info."""
    ticker = yf.Ticker(symbol)

    # Try fast_info first (more reliable in yfinance >= 0.2)
    try:
        fi = ticker.fast_info
        price = getattr(fi, "last_price", None)
        prev  = getattr(fi, "previous_close", None) or getattr(fi, "regular_market_previous_close", None)
        if price and price > 0:
            change     = round(price - prev, 4) if prev else None
            pct_change = round((change / prev) * 100, 4) if (change is not None and prev) else None
            return {
                "regularMarketPrice":         price,
                "regularMarketChange":        change,
                "regularMarketChangePercent": pct_change,
                "regularMarketVolume":        getattr(fi, "last_volume", None) or getattr(fi, "three_month_average_volume", None),
                "marketCap":                  getattr(fi, "market_cap", None),
                "longName":                   None,  # fast_info doesn't have name
                "shortName":                  None,
                "_from_fast_info":            True,
            }
    except Exception:
        pass

    # Fallback to full info
    info = ticker.info
    if not info or (info.get("regularMarketPrice") is None and info.get("currentPrice") is None):
        raise ValueError(f"yfinance returned empty info for {symbol}")
    return info


# ---------------------------------------------------------------------------
# Direct Yahoo quote endpoint (fallback path)
# Try multiple base URLs for robustness
# ---------------------------------------------------------------------------

YF_CHART_URLS = [
    "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d",
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d",
]

# Yahoo v10 quoteSummary — richer data, also tried as fallback
YF_SUMMARY_URL = (
    "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
    "?modules=price,defaultKeyStatistics,summaryDetail"
)


def _fetch_via_direct_api(symbol: str) -> dict:
    """Try multiple Yahoo Finance API endpoints, return meta dict from first success."""
    last_exc: Exception = RuntimeError("No URLs tried")

    # Try chart endpoints
    for url_tpl in YF_CHART_URLS:
        url = url_tpl.format(symbol=symbol)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            result = data.get("chart", {}).get("result") or []
            if result:
                return result[0]["meta"]
        except Exception as exc:
            last_exc = exc
            logger.debug("Chart URL %s failed: %s", url, exc)

    # Try quoteSummary as last resort
    try:
        url = YF_SUMMARY_URL.format(symbol=symbol)
        resp = requests.get(url, headers=HEADERS, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        price_module = (
            data.get("quoteSummary", {})
            .get("result", [{}])[0]
            .get("price", {})
        )
        if price_module:
            return {
                "regularMarketPrice":         price_module.get("regularMarketPrice", {}).get("raw"),
                "regularMarketChange":        price_module.get("regularMarketChange", {}).get("raw"),
                "regularMarketChangePercent": price_module.get("regularMarketChangePercent", {}).get("raw"),
                "regularMarketVolume":        price_module.get("regularMarketVolume", {}).get("raw"),
                "longName":                   price_module.get("longName"),
                "shortName":                  price_module.get("shortName"),
                "_from_summary":              True,
            }
    except Exception as exc:
        last_exc = exc
        logger.debug("quoteSummary URL failed: %s", exc)

    raise last_exc


# ---------------------------------------------------------------------------
# Public fetch function
# ---------------------------------------------------------------------------

def fetch(symbol: str) -> AdapterResult:
    """
    Fetch stock data from Yahoo Finance.

    Args:
        symbol: Exchange-qualified symbol, e.g. "ZOMATO.NS" or "AAPL"

    Returns:
        AdapterResult with success=True on success, or success=False with
        error message on any failure.
    """
    now = datetime.now(timezone.utc)

    # ---- Attempt 1: yfinance ----
    info: Optional[dict] = None
    try:
        info = _fetch_via_yfinance(symbol)
        logger.debug("yfinance succeeded for %s", symbol)
    except Exception as exc:
        logger.warning("yfinance failed for %s: %s — trying direct API", symbol, exc)

    if info:
        price      = _safe_float(info.get("regularMarketPrice") or info.get("currentPrice"))
        change     = _safe_float(info.get("regularMarketChange"))
        pct_change = _safe_float(info.get("regularMarketChangePercent"))
        volume     = _safe_int(info.get("regularMarketVolume") or info.get("volume"))
        mktcap     = _safe_float(info.get("marketCap"))
        pe         = _safe_float(info.get("trailingPE") or info.get("forwardPE"))
        div_raw    = _safe_float(info.get("dividendYield"))
        div_yld    = round(div_raw * 100, 4) if div_raw is not None else None
        name       = info.get("longName") or info.get("shortName") or ""

        if price is not None and price > 0:
            return AdapterResult(
                ticker=symbol,
                name=name or symbol,
                last_price=price,
                change=change,
                pct_change=pct_change,
                volume=volume,
                market_cap=mktcap,
                pe_ratio=pe,
                div_yield=div_yld,
                source=SOURCE,
                fetched_at=now,
                success=True,
            )
        info = None  # price was None — fall through to direct API

    # ---- Attempt 2: direct Yahoo endpoints ----
    try:
        meta = _fetch_via_direct_api(symbol)
        price      = _safe_float(meta.get("regularMarketPrice") or meta.get("previousClose"))
        change     = _safe_float(meta.get("regularMarketChange"))
        pct_change = _safe_float(meta.get("regularMarketChangePercent"))
        volume     = _safe_int(meta.get("regularMarketVolume"))
        name       = meta.get("longName") or meta.get("shortName") or symbol

        if price is None or price <= 0:
            raise ValueError("No valid price in direct API response")

        logger.debug("Direct Yahoo API succeeded for %s", symbol)
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
            source=f"{SOURCE}_direct",
            fetched_at=now,
            success=True,
        )
    except Exception as exc:
        error_msg = f"All Yahoo paths failed: {exc}"
        logger.error("Yahoo adapter totally failed for %s: %s", symbol, error_msg)
        return AdapterResult(
            ticker=symbol,
            source=SOURCE,
            fetched_at=now,
            success=False,
            error=error_msg,
        )

