"""
cache.py — In-Memory Cache Layer (Stage 7).

Separate TTLs for:
  - Price data:  short TTL (30 seconds) — keeps data "fresh"
  - Resolver:    long TTL  (6 hours)    — symbol mapping is stable

Uses cachetools.TTLCache for thread-safe, auto-expiring storage.
"""

from __future__ import annotations

import threading
from typing import Optional

from cachetools import TTLCache

# ---------------------------------------------------------------------------
# Cache stores
# ---------------------------------------------------------------------------

_PRICE_TTL    = 30          # seconds
_RESOLVER_TTL = 6 * 3600    # 6 hours

_price_cache:    TTLCache = TTLCache(maxsize=512, ttl=_PRICE_TTL)
_resolver_cache: TTLCache = TTLCache(maxsize=1024, ttl=_RESOLVER_TTL)
_price_lock    = threading.Lock()
_resolver_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Price cache
# ---------------------------------------------------------------------------

def get_price(symbol: str) -> Optional[dict]:
    """Return cached price record for symbol, or None if not cached / expired."""
    with _price_lock:
        return _price_cache.get(symbol)


def set_price(symbol: str, record: dict) -> None:
    """Cache a price record for symbol."""
    with _price_lock:
        _price_cache[symbol] = record


def invalidate_price(symbol: str) -> None:
    """Remove a specific symbol from the price cache."""
    with _price_lock:
        _price_cache.pop(symbol, None)


# ---------------------------------------------------------------------------
# Resolver cache
# ---------------------------------------------------------------------------

def get_resolver(query: str) -> Optional[dict]:
    """Return cached resolver result for query, or None."""
    with _resolver_lock:
        return _resolver_cache.get(query.lower())


def set_resolver(query: str, result: dict) -> None:
    """Cache a resolver result for query."""
    with _resolver_lock:
        _resolver_cache[query.lower()] = result


# ---------------------------------------------------------------------------
# Stats (for debugging / monitoring)
# ---------------------------------------------------------------------------

def stats() -> dict:
    with _price_lock:
        price_size = len(_price_cache)
    with _resolver_lock:
        resolver_size = len(_resolver_cache)
    return {
        "price_cache_entries":    price_size,
        "resolver_cache_entries": resolver_size,
        "price_ttl_seconds":      _PRICE_TTL,
        "resolver_ttl_seconds":   _RESOLVER_TTL,
    }
