"""
resolver.py — Ticker Resolver (Stage 2).
Converts a cleaned query into an exchange-qualified symbol.

Sources used (all free, no API key):
  1. Yahoo Finance autocomplete endpoint
  2. NSE India search endpoint (for Indian-intended queries)
"""

from __future__ import annotations

import logging
import re
import time
from functools import lru_cache
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

YF_SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"
NSE_SEARCH_URL = "https://www.nseindia.com/api/search-autocomplete?q={query}"
NSE_HOME_URL   = "https://www.nseindia.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "application/json, text/plain, */*",
}

# Exchanges we treat as "Indian"
INDIAN_EXCHANGES = {"NSI", "BSE", "NSE"}

# Map from Yahoo exchange codes → our canonical exchange names
YF_EXCHANGE_MAP = {
    "NSI":    "NSE",
    "BSE":    "BSE",
    "NYSE":   "NYSE",
    "NMS":    "NASDAQ",
    "NGM":    "NASDAQ",
    "NCM":    "NASDAQ",
    "PCX":    "NYSE",
    "ASE":    "NYSE",
    "AMEX":   "AMEX",
}


# ---------------------------------------------------------------------------
# Heuristics
# ---------------------------------------------------------------------------

def _looks_indian(query: str, yf_exchange: str = "") -> bool:
    """Guess whether query is intended for Indian markets."""
    if yf_exchange in INDIAN_EXCHANGES:
        return True
    # Known Indian suffixes
    if re.search(r"\.(NS|BO)$", query, re.IGNORECASE):
        return True
    # Common Indian company name keywords
    indian_keywords = [
        "nse", "bse", "india", "ltd", "limited", "infosy", "reliance",
        "tcs", "wipro", "swiggy", "zomato", "paytm", "nykaa", "ola",
        "adani", "tata", "bajaj", "hdfc", "icici", "sbi", "infosys",
    ]
    q_lower = query.lower()
    return any(kw in q_lower for kw in indian_keywords)


# ---------------------------------------------------------------------------
# Yahoo Finance search
# ---------------------------------------------------------------------------

def _search_yahoo(query: str, timeout: int = 6) -> list[dict]:
    """
    Call Yahoo Finance's autocomplete endpoint.
    Returns a list of candidate dicts with keys:
      symbol, exchange, longname / shortname
    """
    params = {
        "q": query,
        "quotesCount": 10,
        "newsCount": 0,
        "listsCount": 0,
        "enableFuzzyQuery": True,
        "enableCb": True,
        "enableNavLinks": False,
    }
    try:
        resp = requests.get(
            YF_SEARCH_URL, params=params, headers=HEADERS, timeout=timeout
        )
        resp.raise_for_status()
        data = resp.json()
        quotes = data.get("quotes", [])
        results = []
        for q in quotes:
            if q.get("quoteType") not in ("EQUITY", "ETF", "MUTUALFUND"):
                continue
            results.append({
                "symbol":   q.get("symbol", ""),
                "exchange": q.get("exchange", ""),
                "name":     q.get("longname") or q.get("shortname") or "",
                "type":     q.get("quoteType", ""),
            })
        return results
    except Exception as exc:
        logger.warning("Yahoo search failed for %r: %s", query, exc)
        return []


# ---------------------------------------------------------------------------
# NSE India search (requires session handshake)
# ---------------------------------------------------------------------------

def _get_nse_session() -> requests.Session:
    """Create a requests.Session with NSE cookies obtained via homepage visit."""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.headers["Referer"] = NSE_HOME_URL
    try:
        session.get(NSE_HOME_URL, timeout=8)
        time.sleep(0.5)  # Brief pause after handshake
    except Exception as exc:
        logger.warning("NSE session handshake failed: %s", exc)
    return session


def _search_nse(query: str, session: Optional[requests.Session] = None) -> list[dict]:
    """Query NSE India's autocomplete endpoint."""
    if session is None:
        session = _get_nse_session()
    url = NSE_SEARCH_URL.format(query=requests.utils.quote(query))
    try:
        resp = session.get(url, timeout=6)
        resp.raise_for_status()
        data = resp.json()
        results = []
        # NSE returns: {"symbols": [{"symbol": "ZOMATO", "name_of_company": "...", ...}], ...}
        for item in data.get("symbols", []):
            sym = item.get("symbol") or item.get("nsCode") or ""
            name = item.get("name_of_company") or item.get("company_name") or ""
            if sym:
                results.append({
                    "symbol":   sym + ".NS",
                    "exchange": "NSE",
                    "name":     name,
                    "type":     "EQUITY",
                })
        return results
    except Exception as exc:
        logger.warning("NSE search failed for %r: %s", query, exc)
        return []


# ---------------------------------------------------------------------------
# Screener.in search (best for Indian company name → NSE ticker mapping)
# ---------------------------------------------------------------------------

SCREENER_SEARCH_URL = "https://www.screener.in/api/company/search/?q={query}&fields=name,ticker"

def _search_screener(query: str) -> list[dict]:
    """
    Search Screener.in for Indian company tickers.
    Returns: list of {symbol, exchange, name, type, source}

    Screener's API returns: [{id, name, url}, ...]
    The url looks like: /company/ETERNAL/consolidated/
    We extract the ticker from the URL path.
    """
    url = SCREENER_SEARCH_URL.format(query=requests.utils.quote(query))
    try:
        resp = requests.get(url, headers=HEADERS, timeout=6)
        if not resp.ok:
            return []
        results = resp.json()
        candidates = []
        for item in results:
            name      = item.get("name") or ""
            # Extract ticker from URL: /company/ETERNAL/consolidated/ → ETERNAL
            item_url  = item.get("url") or ""
            parts     = [p for p in item_url.split("/") if p]
            # URL format: ['company', 'ETERNAL', 'consolidated']
            ticker    = parts[1].upper() if len(parts) >= 2 and parts[0] == "company" else ""
            if not ticker:
                # Fallback: try 'ticker' field directly (may be present in some responses)
                ticker = (item.get("ticker") or "").upper()
            if ticker:
                candidates.append({
                    "symbol":   ticker + ".NS",
                    "exchange": "NSE",
                    "name":     name,
                    "type":     "EQUITY",
                    "source":   "screener",   # flag for scoring boost
                })
        logger.debug("Screener found %d candidates for %r", len(candidates), query)
        return candidates
    except Exception as exc:
        logger.debug("Screener search failed for %r: %s", query, exc)
        return []

def _score_candidate(candidate: dict, query: str) -> int:
    """Higher score = better match."""
    score = 0
    name   = (candidate.get("name") or "").lower()
    symbol = (candidate.get("symbol") or "").lower()
    q      = query.lower()

    # Exact name match
    if q == name:
        score += 100
    elif q in name:
        score += 50
    # Exact symbol match (ignoring exchange suffix)
    base_sym = symbol.split(".")[0]
    if q == base_sym:
        score += 80
    elif q in base_sym:
        score += 30
    # Prefer equities over ETFs/funds
    if candidate.get("type") == "EQUITY":
        score += 10
    # Screener.in results are always relevant Indian companies — boost them
    # so they beat unrelated Yahoo results (e.g. Zomato query → Eternal.NS from Screener
    # beats Chinese company 603767.SS from Yahoo)
    if candidate.get("source") == "screener":
        score += 60
    return score



def _pick_best(candidates: list[dict], query: str) -> tuple[dict, str]:
    """
    Return (best_candidate, confidence).
    confidence: "exact" if top score is unambiguously high, else "fuzzy".
    """
    if not candidates:
        return {}, "none"

    scored = sorted(candidates, key=lambda c: _score_candidate(c, query), reverse=True)
    best  = scored[0]
    top_score = _score_candidate(best, query)

    confidence = "exact" if top_score >= 50 else "fuzzy"
    return best, confidence


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve(query: str) -> dict:
    """
    Resolve a cleaned query string to an exchange-qualified symbol.

    Special case: if the query already looks like a qualified ticker
    (e.g. "ZOMATO.NS", "AAPL"), we use it directly and just confirm
    via Yahoo search — avoiding "no results" from passing ".NS" to NSE search.

    Returns:
        {
          "symbol": "ZOMATO.NS",
          "exchange": "NSE",
          "resolved_name": "Zomato Limited",
          "confidence": "exact",
          "candidates": [...],
        }
    Returns dict with "symbol": "" on total failure.
    """
    # ---- Fast path: query already looks like a ticker ----
    # e.g. "ZOMATO.NS", "AAPL", "COLPAL.NS"
    is_qualified = bool(re.match(r"^[A-Z0-9&]+(\.[A-Z]{1,4})?$", query))

    if is_qualified:
        # Use it as-is; confirm via Yahoo to get name + exchange
        yf_candidates = _search_yahoo(query.split(".")[0])  # search base symbol
        # Find exact match in candidates
        exact = next(
            (c for c in yf_candidates if c["symbol"].upper() == query.upper()),
            None,
        )
        if exact:
            exchange_raw = exact.get("exchange", "")
            return {
                "symbol":        exact["symbol"],
                "exchange":      YF_EXCHANGE_MAP.get(exchange_raw, exchange_raw),
                "resolved_name": exact.get("name", query),
                "confidence":    "exact",
                "candidates":    yf_candidates,
            }
        # Yahoo didn't return it — construct from suffix heuristic
        suffix = query.rsplit(".", 1)[-1].upper() if "." in query else ""
        exchange_from_suffix = {
            "NS": "NSE", "BO": "BSE", "US": "NYSE",
        }.get(suffix, "")
        return {
            "symbol":        query.upper(),
            "exchange":      exchange_from_suffix or "NSE",
            "resolved_name": query,
            "confidence":    "fuzzy",
            "candidates":    yf_candidates,
        }

    # ---- Normal path: name/partial ticker search ----

    # Phase 1: Yahoo search
    yf_candidates = _search_yahoo(query)
    logger.debug("Yahoo candidates for %r: %s", query, yf_candidates)

    # Phase 2: Screener.in for Indian companies (best for NSE; handles renames like Zomato→Eternal)
    screener_candidates: list[dict] = []
    if _looks_indian(query, yf_candidates[0]["exchange"] if yf_candidates else ""):
        screener_candidates = _search_screener(query)
        logger.debug("Screener candidates for %r: %s", query, screener_candidates)

    # Phase 3: NSE autocomplete (skipped gracefully if NSE blocks)
    nse_candidates: list[dict] = []
    if _looks_indian(query, yf_candidates[0]["exchange"] if yf_candidates else ""):
        nse_candidates = _search_nse(query)
        logger.debug("NSE candidates for %r: %s", query, nse_candidates)

    # Merge: Screener results highest priority for Indian tickers (most accurate for renames)
    all_candidates = screener_candidates + nse_candidates + yf_candidates

    best, confidence = _pick_best(all_candidates, query)

    if not best:
        logger.warning("No candidates found for query %r", query)
        return {
            "symbol": "",
            "exchange": "",
            "resolved_name": "",
            "confidence": "none",
            "candidates": [],
        }

    exchange_raw  = best.get("exchange", "")
    exchange_canonical = YF_EXCHANGE_MAP.get(exchange_raw, exchange_raw)

    return {
        "symbol":        best["symbol"],
        "exchange":      exchange_canonical,
        "resolved_name": best.get("name", ""),
        "confidence":    confidence,
        "candidates":    all_candidates,
    }

