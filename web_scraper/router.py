"""
router.py — Adapter Router + Field-Level Merger (Stages 3 & 5).

The router decides which adapters to call and in what order,
based on the resolved exchange.  The merger then picks the best
non-null value for each field across all adapter results.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from schema import AdapterResult, StockRecord

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Adapter priority table (data-driven, not hardcoded per ticker)
# ---------------------------------------------------------------------------
# Each entry maps an exchange pattern to an ordered list of adapter names.
# The router iterates this list left-to-right until it has a full record
# or exhausts all adapters.

ADAPTER_PRIORITY: dict[str, list[str]] = {
    "NSE":    ["yahoo", "india", "stooq"],
    "BSE":    ["yahoo", "india", "stooq"],
    "NYSE":   ["yahoo", "stooq"],
    "NASDAQ": ["yahoo", "stooq"],
    "AMEX":   ["yahoo", "stooq"],
    "DEFAULT": ["yahoo", "india", "stooq"],   # catch-all for any other exchange
}

# Ordered list of fields; earlier entries have "higher priority" in the
# final merged record (determines which source is logged as the field source).
MERGE_FIELDS = [
    "name", "last_price", "change", "pct_change",
    "volume", "market_cap", "pe_ratio", "div_yield",
]


# ---------------------------------------------------------------------------
# Lazy adapter loader (avoids circular imports and keeps startup fast)
# ---------------------------------------------------------------------------

def _load_adapter(name: str):
    """Return the adapter module for the given name."""
    if name == "yahoo":
        from adapters import yahoo
        return yahoo
    if name == "nse":
        from adapters import nse
        return nse
    if name == "india":
        from adapters import india
        return india
    if name == "stooq":
        from adapters import stooq
        return stooq
    raise ValueError(f"Unknown adapter: {name!r}")


# ---------------------------------------------------------------------------
# Field-level merger
# ---------------------------------------------------------------------------

def _merge(results: list[AdapterResult], symbol: str) -> Optional[dict]:
    """
    Merge multiple AdapterResult objects field by field.
    For each field, take the first non-null value from the highest-priority
    successful adapter.

    Returns a dict suitable for constructing StockRecord, or None if all
    adapters failed.
    """
    successful = [r for r in results if r.success]
    if not successful:
        logger.error("All adapters failed for %s", symbol)
        return None

    merged: dict = {}
    field_sources: dict[str, str] = {}

    for field in MERGE_FIELDS:
        for result in successful:
            val = getattr(result, field, None)
            if val is not None:
                merged[field] = val
                field_sources[field] = result.source
                break
        else:
            merged[field] = None

    merged["ticker"]       = symbol
    merged["field_sources"] = field_sources
    merged["fetched_at"]   = successful[0].fetched_at or datetime.now(timezone.utc)
    merged["source"]       = ", ".join(r.source for r in successful)

    return merged


# ---------------------------------------------------------------------------
# Public fetch-and-merge function
# ---------------------------------------------------------------------------

def fetch_and_merge(
    symbol: str,
    exchange: str,
    resolved_name: str = "",
    confidence: str = "exact",
) -> Optional[dict]:
    """
    Run adapters in priority order for the given exchange, then merge results.

    Returns a dict ready to build a StockRecord, or None on total failure.
    """
    adapter_names = ADAPTER_PRIORITY.get(exchange, ADAPTER_PRIORITY["DEFAULT"])
    logger.info(
        "Router: %s (%s) → adapters: %s", symbol, exchange, adapter_names
    )

    results: list[AdapterResult] = []

    for adapter_name in adapter_names:
        adapter = _load_adapter(adapter_name)
        logger.debug("Calling %s adapter for %s", adapter_name, symbol)
        try:
            result = adapter.fetch(symbol)
            results.append(result)
            if result.success:
                logger.debug(
                    "%s adapter succeeded for %s: price=%s",
                    adapter_name, symbol, result.last_price
                )
            else:
                logger.warning(
                    "%s adapter failed for %s: %s",
                    adapter_name, symbol, result.error
                )
        except Exception as exc:
            logger.error(
                "Unexpected exception from %s adapter for %s: %s",
                adapter_name, symbol, exc, exc_info=True
            )
            results.append(AdapterResult(
                ticker=symbol,
                source=adapter_name,
                fetched_at=datetime.now(timezone.utc),
                success=False,
                error=str(exc),
            ))

    merged = _merge(results, symbol)
    if merged is None:
        return None

    # Inject resolver metadata
    merged["resolved_exchange"] = exchange
    merged["confidence"]        = confidence
    # Use resolver name if no adapter provided one
    if not merged.get("name") and resolved_name:
        merged["name"] = resolved_name

    return merged
