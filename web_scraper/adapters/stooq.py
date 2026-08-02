"""
adapters/stooq.py — Stooq Adapter (Stage 4c).

Stooq provides a free CSV endpoint with no authentication required.
This is the last-resort fallback — it only supplies price/volume/change.

Returns an AdapterResult.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from schema import AdapterResult

logger = logging.getLogger(__name__)

SOURCE = "stooq"

# Stooq CSV endpoint. Symbol format differs by exchange:
#   US:    AAPL.US
#   India: ZOMATO.IN  (NSE-listed equities)
STOOQ_URL = "https://stooq.com/q/l/?s={symbol}&f=sd2t2ohlcvn&h&e=csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
}

# ---------------------------------------------------------------------------
# Symbol mapping helpers
# ---------------------------------------------------------------------------

def _to_stooq_symbol(symbol: str) -> str:
    """
    Convert an exchange-qualified symbol to Stooq format.

    Stooq expects lowercase symbols:
      ZOMATO.NS → zomato.in
      AAPL      → aapl.us
      COLPAL.NS → colpal.in
    """
    s = symbol.upper()
    if s.endswith(".NS") or s.endswith(".BO"):
        base = s.rsplit(".", 1)[0]
        return f"{base}.in".lower()
    if "." not in s:
        return f"{s}.us".lower()
    # Already has a suffix — just lowercase it
    return s.lower()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_float(value: str) -> Optional[float]:
    try:
        v = float(value)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def _safe_int(value: str) -> Optional[int]:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Fetch with retry
# ---------------------------------------------------------------------------

@retry(
    retry=retry_if_exception_type(requests.RequestException),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    reraise=True,
)
def _fetch_csv(stooq_sym: str) -> str:
    url = STOOQ_URL.format(symbol=requests.utils.quote(stooq_sym, safe=""))
    resp = requests.get(url, headers=HEADERS, timeout=8)
    resp.raise_for_status()
    return resp.text


# ---------------------------------------------------------------------------
# Public fetch function
# ---------------------------------------------------------------------------

def fetch(symbol: str) -> AdapterResult:
    """
    Fetch stock data from Stooq (CSV endpoint).

    Args:
        symbol: Exchange-qualified symbol, e.g. "ZOMATO.NS" or "AAPL"

    Returns:
        AdapterResult
    """
    now = datetime.now(timezone.utc)
    stooq_sym = _to_stooq_symbol(symbol)

    try:
        csv_text = _fetch_csv(stooq_sym)
    except Exception as exc:
        return AdapterResult(
            ticker=symbol,
            source=SOURCE,
            fetched_at=now,
            success=False,
            error=f"Stooq fetch failed: {exc}",
        )

    # Parse CSV: header + 1 data row
    # Header: Symbol,Date,Time,Open,High,Low,Close,Volume,Name
    lines = [ln.strip() for ln in csv_text.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return AdapterResult(
            ticker=symbol,
            source=SOURCE,
            fetched_at=now,
            success=False,
            error=f"Stooq returned no data rows for {stooq_sym}",
        )

    header = [h.strip() for h in lines[0].split(",")]
    row    = [r.strip() for r in lines[1].split(",")]

    if len(row) < len(header):
        return AdapterResult(
            ticker=symbol,
            source=SOURCE,
            fetched_at=now,
            success=False,
            error=f"Stooq CSV row too short: {row}",
        )

    d = dict(zip(header, row))

    close_price = _safe_float(d.get("Close"))
    open_price  = _safe_float(d.get("Open"))
    volume      = _safe_int(d.get("Volume"))
    name        = d.get("Name") or symbol

    if close_price is None or close_price == 0:
        return AdapterResult(
            ticker=symbol,
            source=SOURCE,
            fetched_at=now,
            success=False,
            error=f"Stooq returned zero/null close price for {stooq_sym}. Row: {d}",
        )

    # Stooq gives open and close — compute day-change approximation
    change: Optional[float] = None
    pct_change: Optional[float] = None
    if open_price and open_price != 0:
        change     = round(close_price - open_price, 4)
        pct_change = round((change / open_price) * 100, 4)

    return AdapterResult(
        ticker=symbol,
        name=name,
        last_price=close_price,
        change=change,
        pct_change=pct_change,
        volume=volume,
        market_cap=None,   # Stooq doesn't provide
        pe_ratio=None,
        div_yield=None,
        source=SOURCE,
        fetched_at=now,
        success=True,
    )
