"""
scraper.py — Main Pipeline Orchestrator.

Public API:
    fetch_stock(query: str) -> dict

Wires all stages together:
  1. Normalize input
  2. Resolve ticker (with cache)
  3. Route to adapters + merge (with cache)
  4. Validate with Pydantic schema
  5. Return final JSON-serialisable dict
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import cache
import normalizer
import resolver
import router
from schema import StockRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Logging setup (call once at import time)
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
# Quieten noisy sub-libraries
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("yfinance").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def fetch_stock(query: str, force_refresh: bool = False) -> dict:
    """
    Fetch stock data for any ticker or company name.

    Args:
        query:         Ticker symbol or company name (any exchange).
        force_refresh: Skip cache and re-fetch fresh data.

    Returns:
        dict with keys:
          ticker, name, last_price, change, pct_change,
          volume, market_cap, pe_ratio, div_yield,
          source, field_sources, fetched_at, confidence,
          resolved_exchange

        On total failure, returns:
          {"error": "<message>", "query": query}
    """
    # ---- Stage 1: Normalize ----
    clean_query = normalizer.normalize(query)
    logger.info("Query %r → normalized %r", query, clean_query)

    # ---- Stage 7 (cache check) ----
    cached_resolver = cache.get_resolver(clean_query)
    if cached_resolver and not force_refresh:
        logger.debug("Resolver cache HIT for %r", clean_query)
        resolved = cached_resolver
    else:
        # ---- Stage 2: Resolve ticker ----
        resolved = resolver.resolve(clean_query)
        if not resolved.get("symbol"):
            msg = (
                f"Could not resolve ticker for {query!r}. "
                "Try a more specific query or use a full ticker symbol like 'ZOMATO.NS'."
            )
            logger.warning(msg)
            return {"error": msg, "query": query}

        cache.set_resolver(clean_query, resolved)
        logger.info(
            "Resolved %r → %s (%s) [confidence: %s]",
            clean_query,
            resolved["symbol"],
            resolved["exchange"],
            resolved["confidence"],
        )

        # If confidence is fuzzy, include a warning (but still proceed)
        if resolved["confidence"] == "fuzzy":
            logger.warning(
                "Fuzzy match for %r → %s. "
                "Consider verifying with candidates: %s",
                clean_query,
                resolved["symbol"],
                [c.get("symbol") for c in resolved.get("candidates", [])[:5]],
            )

    symbol   = resolved["symbol"]
    exchange = resolved["exchange"]

    # Check price cache
    cached_price = cache.get_price(symbol)
    if cached_price and not force_refresh:
        logger.debug("Price cache HIT for %s", symbol)
        return cached_price

    # ---- Stages 3–5: Router + Adapters + Merger ----
    merged = router.fetch_and_merge(
        symbol=symbol,
        exchange=exchange,
        resolved_name=resolved.get("resolved_name", ""),
        confidence=resolved.get("confidence", "exact"),
    )

    if merged is None:
        msg = (
            f"All data sources failed for {symbol} ({exchange}). "
            "Data is temporarily unavailable — please try again shortly."
        )
        logger.error(msg)
        return {"error": msg, "query": query, "symbol": symbol}

    # ---- Stage 6: Validate with Pydantic ----
    try:
        record = StockRecord(**merged)
    except Exception as exc:
        logger.error(
            "Schema validation failed for %s: %s | Raw merged data: %s",
            symbol, exc, merged,
        )
        return {
            "error":  f"Data validation failed: {exc}",
            "query":  query,
            "symbol": symbol,
            "raw":    merged,
        }

    # ---- Serialize ----
    result = record.model_dump()

    # Convert datetime to ISO string for JSON serialisability
    if isinstance(result.get("fetched_at"), datetime):
        result["fetched_at"] = result["fetched_at"].isoformat()

    # ---- Cache and return ----
    cache.set_price(symbol, result)
    return result


# ---------------------------------------------------------------------------
# Convenience: pretty-print helper
# ---------------------------------------------------------------------------

def print_stock(query: str) -> None:
    """Fetch and pretty-print a stock record."""
    result = fetch_stock(query)
    if "error" in result:
        print(f"\n[ERROR]  {result['error']}\n")
        return

    width = 52
    sep   = "─" * width

    def fmt_num(val, decimals=2, suffix=""):
        if val is None:
            return "N/A"
        if isinstance(val, float):
            return f"{val:,.{decimals}f}{suffix}"
        return f"{val:,}{suffix}"

    def fmt_mktcap(val, exch=""):
        if val is None:
            return "N/A"
        currency = "Rs." if exch in ("NSE", "BSE") else "$"
        if val >= 1e12:
            return f"{currency}{val/1e12:.2f}T"
        if val >= 1e9:
            return f"{currency}{val/1e9:.2f}B"
        if val >= 1e7 and exch in ("NSE", "BSE"):
            return f"{currency}{val/1e7:.2f}Cr"
        return fmt_num(val)

    change_val = result.get('change') or 0
    change_sign = "+" if change_val >= 0 else "-"
    pct_val = result.get('pct_change') or 0
    exchange = result.get('resolved_exchange', '')

    lines = [
        f"\n{'':>4}{'STOCK DATA':^{width}}",
        sep,
        f"  Ticker         : {result['ticker']}",
        f"  Name           : {result['name']}",
        f"  Exchange       : {result['resolved_exchange']}",
        sep,
        f"  Last Price     : {fmt_num(result['last_price'])}",
        f"  Change         : {change_sign}{fmt_num(abs(change_val))}",
        f"  % Change       : {change_sign}{fmt_num(abs(pct_val))}%",
        f"  Volume         : {fmt_num(result.get('volume'), 0)}",
        sep,
        f"  Market Cap     : {fmt_mktcap(result.get('market_cap'), exchange)}",
        f"  P/E Ratio      : {fmt_num(result.get('pe_ratio'))}",
        f"  Dividend Yield : {fmt_num(result.get('div_yield'))}%",
        sep,
        f"  Source(s)      : {result.get('source', 'N/A')}",
        f"  Confidence     : {result.get('confidence', 'N/A')}",
        f"  Fetched At     : {result.get('fetched_at', 'N/A')}",
        sep,
    ]

    # Field sources (for transparency)
    fs = result.get("field_sources", {})
    if fs:
        lines.append(f"  Field sources  :")
        for fld, src in fs.items():
            lines.append(f"    {fld:<14}: {src}")
        lines.append(sep)

    import io
    out = "\n".join(lines)
    sys.stdout.buffer.write(out.encode("utf-8", errors="replace") + b"\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scraper.py <ticker_or_company_name> [ticker2 ...]")
        print("Examples:")
        print("  python scraper.py AAPL")
        print("  python scraper.py ZOMATO.NS")
        print("  python scraper.py swiggy")
        print("  python scraper.py 'adani enterprises'")
        sys.exit(1)

    queries = sys.argv[1:]
    for q in queries:
        print_stock(q)
