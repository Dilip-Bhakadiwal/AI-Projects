"""
tests/test_sanity.py — Sanity test suite.

Covers the full pipeline (all 7 stages) for a representative set of tickers
spanning US and Indian exchanges, including edge cases from the spec.

Run with:
    python -m pytest tests/ -v
or:
    python tests/test_sanity.py
"""

from __future__ import annotations

import sys
import os
import time

# Ensure project root is on the path when running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scraper
from schema import StockRecord

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------
# Each entry: (description, query, expected_exchange_hint, must_have_price)

TEST_CASES = [
    # --- US stocks (baseline) ---
    ("Apple Inc (NASDAQ)",         "AAPL",                  "NASDAQ",  True),
    ("Microsoft (NASDAQ)",         "MSFT",                  "NASDAQ",  True),

    # --- Indian stocks (NSE) ---
    ("Zomato (NSE) — baseline",    "ZOMATO.NS",             "NSE",     True),
    ("Infosys (NSE)",              "INFY.NS",               "NSE",     True),
    ("Colgate India (NSE)",        "COLPAL.NS",             "NSE",     True),

    # --- Name-based queries (resolver) ---
    ("Swiggy by name",             "swiggy",                "NSE",     True),
    ("Adani Enterprises by name",  "adani enterprises",     "NSE",     True),
    ("Reliance by name",           "reliance",              "NSE",     True),

    # --- Disambiguation / edge cases ---
    # Colgate: must resolve to Indian NSE listing, not US Colgate-Palmolive
    ("Colgate India via name",     "colgate india",         "NSE",     True),
]

GRACE_CASES = [
    # These may not have full data (new IPOs / unlisted) — just check no crash
    ("Ola — may not be listed",    "ola cabs",              "",        False),
    ("Adani Steel — invalid name", "adani steel",           "",        False),
]

# ---------------------------------------------------------------------------
# Core test runner
# ---------------------------------------------------------------------------

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"


def run_test(description: str, query: str, expected_exchange: str, must_have_price: bool) -> bool:
    """
    Run a single test case.  Returns True on pass.
    """
    print(f"\n{'─'*60}")
    print(f"  Test  : {description}")
    print(f"  Query : {query!r}")

    result = scraper.fetch_stock(query)

    if "error" in result:
        if must_have_price:
            print(f"  {FAIL} — error returned: {result['error']}")
            return False
        else:
            print(f"  {WARN} — error returned (expected for edge case): {result['error']}")
            return True

    # Validate with Pydantic
    try:
        record = StockRecord(**result)
    except Exception as exc:
        print(f"  {FAIL} — schema validation failed: {exc}")
        return False

    # Check price
    if must_have_price and (record.last_price is None or record.last_price <= 0):
        print(f"  {FAIL} — no valid price. Got: {record.last_price}")
        return False

    # Exchange check (loose — just warn)
    if expected_exchange and record.resolved_exchange != expected_exchange:
        print(
            f"  {WARN} — exchange mismatch: expected {expected_exchange!r}, "
            f"got {record.resolved_exchange!r}"
        )

    print(f"  {PASS}")
    print(f"  Ticker : {record.ticker}")
    print(f"  Name   : {record.name}")
    print(f"  Price  : {record.last_price}")
    print(f"  Change : {record.change}  ({record.pct_change}%)")
    print(f"  Volume : {record.volume}")
    print(f"  Mkt Cap: {record.market_cap}")
    print(f"  P/E    : {record.pe_ratio}")
    print(f"  Div Yld: {record.div_yield}%")
    print(f"  Source : {record.source}")
    print(f"  Fields : {record.field_sources}")
    return True


def run_all() -> None:
    results = []

    print("\n" + "═"*60)
    print("  STOCK SCRAPER — SANITY TEST SUITE")
    print("═"*60)

    # Main test cases
    for desc, query, exchange, must_price in TEST_CASES:
        ok = run_test(desc, query, exchange, must_price)
        results.append((desc, ok))
        time.sleep(1.5)  # be polite to free APIs

    # Grace / edge cases
    print(f"\n{'═'*60}")
    print("  EDGE CASE / GRACE TESTS (failures are acceptable)")
    print("═"*60)
    for desc, query, exchange, must_price in GRACE_CASES:
        ok = run_test(desc, query, exchange, must_price)
        results.append((desc, ok))
        time.sleep(1.5)

    # Summary
    passed = sum(1 for _, ok in results if ok)
    total  = len(results)
    print(f"\n{'═'*60}")
    print(f"  Results: {passed}/{total} passed")
    for desc, ok in results:
        status = PASS if ok else FAIL
        print(f"  {status}  {desc}")
    print("═"*60 + "\n")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
