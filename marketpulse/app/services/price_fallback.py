"""
app/services/price_fallback.py — Cloud-friendly stock price fetcher.

yfinance is often blocked on shared cloud hosting (Render, Railway, Heroku)
because Yahoo Finance bans data-center IPs. This module provides alternative
price sources that work reliably in cloud environments:

  1. Yahoo Finance v8 chart API with random user-agent spoofing
  2. Yahoo Finance v10 quoteSummary API
  3. Alternative Finance APIs (stooq CSV, which is open)

Used as a fallback inside get_financial_data() when the main scraper returns 0.
"""
from __future__ import annotations

import random
import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# ── User-agent pool to avoid bot detection on cloud IPs ──────────────────────
_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:126.0) Gecko/20100101 Firefox/126.0",
]

def _rand_headers() -> dict:
    return {
        "User-Agent": random.choice(_UA_POOL),
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://finance.yahoo.com/",
    }


def _try_yahoo_chart(symbol: str) -> Optional[dict]:
    """Yahoo Finance v8 chart API — usually works even from cloud IPs."""
    urls = [
        f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d&includePrePost=false",
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d&includePrePost=false",
    ]
    for url in urls:
        try:
            time.sleep(random.uniform(0.3, 0.8))  # polite random delay
            r = requests.get(url, headers=_rand_headers(), timeout=10)
            if r.status_code == 200:
                data = r.json()
                result = (data.get("chart") or {}).get("result") or []
                if result:
                    meta = result[0].get("meta", {})
                    price = meta.get("regularMarketPrice") or meta.get("previousClose")
                    if price and float(price) > 0:
                        return {
                            "price": float(price),
                            "prev_close": meta.get("chartPreviousClose") or meta.get("previousClose"),
                            "currency": meta.get("currency", "USD"),
                            "name": meta.get("longName") or meta.get("shortName") or symbol,
                            "exchange": meta.get("exchangeName", ""),
                            "source": "yahoo_chart_api",
                        }
        except Exception as e:
            logger.debug("yahoo_chart failed for %s: %s", symbol, e)
    return None


def _try_yahoo_quotesummary(symbol: str) -> Optional[dict]:
    """Yahoo Finance v10 quoteSummary — rich metadata including P/E."""
    url = (
        f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
        "?modules=price,defaultKeyStatistics"
    )
    try:
        time.sleep(random.uniform(0.3, 0.8))
        r = requests.get(url, headers=_rand_headers(), timeout=10)
        if r.status_code == 200:
            data = r.json()
            result = ((data.get("quoteSummary") or {}).get("result") or [{}])[0]
            price_module = result.get("price") or {}
            price = (price_module.get("regularMarketPrice") or {}).get("raw")
            if price and float(price) > 0:
                prev = (price_module.get("regularMarketPreviousClose") or {}).get("raw")
                change = (price_module.get("regularMarketChange") or {}).get("raw")
                pct = (price_module.get("regularMarketChangePercent") or {}).get("raw")
                mktcap = (price_module.get("marketCap") or {}).get("raw")
                return {
                    "price": float(price),
                    "prev_close": float(prev) if prev else None,
                    "change_val": float(change) if change else None,
                    "change_pct": float(pct) * 100 if pct else None,
                    "currency": price_module.get("currency", "USD"),
                    "name": price_module.get("longName") or price_module.get("shortName") or symbol,
                    "exchange": (price_module.get("exchangeName") or ""),
                    "market_cap": float(mktcap) if mktcap else None,
                    "source": "yahoo_quotesummary_api",
                }
    except Exception as e:
        logger.debug("yahoo_quotesummary failed for %s: %s", symbol, e)
    return None


def _try_stooq(symbol: str) -> Optional[dict]:
    """Stooq CSV — open data API, no auth required, cloud-friendly."""
    # Stooq uses lowercase symbols with exchange suffix: AAPL -> aapl.us, NVDA -> nvda.us
    sym_lower = symbol.lower()
    # If it already has a dot (e.g. RELIANCE.NS), map to stooq format
    if "." in sym_lower:
        base, exch = sym_lower.rsplit(".", 1)
        stooq_sym = f"{base}.{'in' if exch in ('ns', 'bo') else 'us'}"
    else:
        stooq_sym = f"{sym_lower}.us"

    url = f"https://stooq.com/q/l/?s={stooq_sym}&f=sd2t2ohlcvn&h&e=csv"
    try:
        time.sleep(random.uniform(0.2, 0.5))
        r = requests.get(url, headers=_rand_headers(), timeout=8)
        if r.status_code == 200 and r.text.strip():
            lines = r.text.strip().splitlines()
            if len(lines) >= 2:
                headers = lines[0].split(",")
                values = lines[1].split(",")
                row = dict(zip(headers, values))
                price_str = row.get("Close", "")
                if price_str and price_str not in ("N/D", "null", ""):
                    price = float(price_str)
                    if price > 0:
                        open_px = row.get("Open", "")
                        return {
                            "price": price,
                            "prev_close": None,
                            "change_val": None,
                            "change_pct": None,
                            "currency": "USD",
                            "name": row.get("Name", symbol),
                            "exchange": "stooq",
                            "open_price": float(open_px) if open_px and open_px not in ("N/D", "") else None,
                            "day_high": float(row.get("High", 0) or 0) or None,
                            "day_low": float(row.get("Low", 0) or 0) or None,
                            "source": "stooq_csv",
                        }
    except Exception as e:
        logger.debug("stooq failed for %s: %s", stooq_sym, e)
    return None


def fetch_price_cloud(ticker: str) -> Optional[dict]:
    """
    Cloud-friendly price fetcher. Tries multiple sources in order:
    1. Yahoo Finance chart API (random UA, small delay)
    2. Yahoo Finance quoteSummary API
    3. Stooq CSV API

    Returns a normalized dict with keys:
        price, prev_close, change_val, change_pct, currency, name, exchange, source
    or None if all sources fail.
    """
    symbol = ticker.upper()
    logger.info("price_fallback_attempt", symbol=symbol)

    result = _try_yahoo_chart(symbol)
    if result:
        logger.info("price_fallback_success", symbol=symbol, source=result["source"])
        return result

    result = _try_yahoo_quotesummary(symbol)
    if result:
        logger.info("price_fallback_success", symbol=symbol, source=result["source"])
        return result

    result = _try_stooq(symbol)
    if result:
        logger.info("price_fallback_success", symbol=symbol, source=result["source"])
        return result

    logger.warning("price_fallback_all_failed", symbol=symbol)
    return None
