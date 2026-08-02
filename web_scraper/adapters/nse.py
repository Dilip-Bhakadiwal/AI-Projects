"""
adapters/nse.py — NSE India Adapter (Stage 4b).

Calls NSE India's public quote endpoint (same one used by nseindia.com).
Requires a cookie/session handshake via the NSE homepage first — NSE
blocks bare requests without it.

Returns an AdapterResult.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from schema import AdapterResult

logger = logging.getLogger(__name__)

SOURCE = "nse"

NSE_HOME       = "https://www.nseindia.com"
NSE_QUOTE_URL  = "https://www.nseindia.com/api/quote-equity?symbol={symbol}"
NSE_SERIES_URL = "https://www.nseindia.com/api/quote-equity?symbol={symbol}&series=[%22EQ%22]"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         NSE_HOME,
    "X-Requested-With": "XMLHttpRequest",
}


# ---------------------------------------------------------------------------
# Session management (module-level singleton)
# ---------------------------------------------------------------------------

_session: Optional[requests.Session] = None
_session_created_at: float = 0.0
SESSION_TTL = 600  # Renew session every 10 minutes


def _get_session(force_renew: bool = False) -> requests.Session:
    global _session, _session_created_at

    age = time.time() - _session_created_at
    if _session is None or force_renew or age > SESSION_TTL:
        s = requests.Session()
        s.headers.update(HEADERS)
        try:
            # Hit NSE homepage to get session cookies
            s.get(NSE_HOME, timeout=8)
            time.sleep(0.5)
            # Hit the market-data page to establish a richer cookie set
            s.get(f"{NSE_HOME}/market-data/live-equity-market", timeout=6)
            time.sleep(0.3)
        except Exception as exc:
            logger.warning("NSE session handshake warning: %s", exc)
        _session = s
        _session_created_at = time.time()
        logger.debug("NSE session renewed")
    return _session


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_float(value) -> Optional[float]:
    try:
        v = float(value)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def _safe_int(value) -> Optional[int]:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _strip_ns_suffix(symbol: str) -> str:
    """Convert 'ZOMATO.NS' → 'ZOMATO'."""
    return symbol.upper().replace(".NS", "").replace(".BO", "")


# ---------------------------------------------------------------------------
# Fetch with retry
# ---------------------------------------------------------------------------

@retry(
    retry=retry_if_exception_type(requests.RequestException),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    reraise=True,
)
def _fetch_nse_quote(nse_symbol: str) -> dict:
    """Fetch the NSE equity quote JSON for a symbol (no .NS suffix)."""
    session = _get_session()
    url = NSE_QUOTE_URL.format(symbol=requests.utils.quote(nse_symbol))
    resp = session.get(url, timeout=8)
    if resp.status_code == 401:
        # Session cookie expired — renew and retry
        _get_session(force_renew=True)
        raise requests.RequestException("NSE 401 — session renewed, will retry")
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Public fetch function
# ---------------------------------------------------------------------------

def fetch(symbol: str) -> AdapterResult:
    """
    Fetch stock data from NSE India.

    Args:
        symbol: Exchange-qualified symbol, e.g. "ZOMATO.NS" or just "ZOMATO"

    Returns:
        AdapterResult
    """
    now = datetime.now(timezone.utc)
    nse_symbol = _strip_ns_suffix(symbol)

    try:
        data = _fetch_nse_quote(nse_symbol)
    except Exception as exc:
        error_msg = f"NSE fetch failed: {exc}"
        logger.error("NSE adapter failed for %s: %s", symbol, error_msg)
        return AdapterResult(
            ticker=symbol,
            source=SOURCE,
            fetched_at=now,
            success=False,
            error=error_msg,
        )

    # ---------- Parse NSE response ----------
    # NSE quote API response shape:
    # {
    #   "info": {"symbol": ..., "companyName": ..., ...},
    #   "priceInfo": {
    #     "lastPrice": ..., "change": ..., "pChange": ...,
    #     "totalTradedVolume": ..., ...
    #   },
    #   "marketDeptOrderBook": {...},
    #   "metadata": {"pdSectorPe": ..., "pdSymbolPe": ..., ...},
    #   "securityInfo": {"dividendYield": ..., ...},
    # }

    info_section  = data.get("info", {})
    price_section = data.get("priceInfo", {})
    meta_section  = data.get("metadata", {})
    sec_section   = data.get("securityInfo", {})

    name       = info_section.get("companyName") or nse_symbol
    price      = _safe_float(price_section.get("lastPrice"))
    change     = _safe_float(price_section.get("change"))
    pct_change = _safe_float(price_section.get("pChange"))
    volume     = _safe_int(price_section.get("totalTradedVolume"))

    # Market cap: NSE gives it in crores sometimes, or we compute from shares*price
    mktcap_raw = _safe_float(
        meta_section.get("marketCap")
        or sec_section.get("totalMarketCap")
    )
    # If given in crores, convert to raw INR
    if mktcap_raw and mktcap_raw < 1e9:
        mktcap = mktcap_raw * 1e7   # crores → rupees
    else:
        mktcap = mktcap_raw

    # P/E: NSE provides pdSymbolPe (symbol-level) and pdSectorPe
    pe_ratio   = _safe_float(
        meta_section.get("pdSymbolPe")
        or sec_section.get("pe")
    )

    # Dividend yield: securityInfo.dividendYield (in %)
    div_yield  = _safe_float(sec_section.get("dividendYield"))

    if price is None:
        return AdapterResult(
            ticker=symbol,
            source=SOURCE,
            fetched_at=now,
            success=False,
            error=f"NSE returned no price for {nse_symbol}. Raw keys: {list(data.keys())}",
        )

    return AdapterResult(
        ticker=symbol,
        name=name,
        last_price=price,
        change=change,
        pct_change=pct_change,
        volume=volume,
        market_cap=mktcap,
        pe_ratio=pe_ratio,
        div_yield=div_yield,
        source=SOURCE,
        fetched_at=now,
        success=True,
    )
