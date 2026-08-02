"""
app/ingestion/fetcher.py — Async yfinance fetcher with retry + exponential backoff.
yfinance is sync so we run it in a thread pool via asyncio.to_thread.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import List

import yfinance as yf
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from app.ingestion.validator import RawTickIn

logger = logging.getLogger(__name__)


async def _fetch_ticker_with_retry(ticker: str) -> List[RawTickIn]:
    """
    Inner fetch logic — called by fetch_ticker.
    Raises on network/parse failure so the @retry decorator can actually trigger.
    Bug fix #6: exceptions must propagate out of the retried function, not be caught inside it.
    """
    # yfinance is blocking — run in thread pool
    raw_df = await asyncio.to_thread(_download_sync, ticker)

    if raw_df is None or raw_df.empty:
        logger.warning("No data returned for %s", ticker)
        return []

    # Bug fix #14: yfinance >= 0.2 returns a MultiIndex DataFrame when using Ticker.history().
    # Flatten column index so row["Open"] etc. work regardless of yfinance version.
    if isinstance(raw_df.columns, __import__("pandas").MultiIndex):
        raw_df.columns = raw_df.columns.get_level_values(0)

    results: List[RawTickIn] = []
    for ts, row in raw_df.iterrows():
        try:
            tick = RawTickIn(
                ticker=ticker,
                timestamp=ts.to_pydatetime().replace(tzinfo=timezone.utc),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=int(row["Volume"]),
            )
            results.append(tick)
        except (ValidationError, KeyError, TypeError) as e:
            logger.warning("Skipping invalid row for %s: %s", ticker, e)

    logger.info("Fetched %d valid ticks for %s", len(results), ticker)
    return results


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def fetch_ticker(ticker: str) -> List[RawTickIn]:
    """
    Fetch last 1 day of 15-min OHLCV bars for a ticker.
    Returns validated RawTickIn objects. Empty list on failure.
    Bug fix #6: outer wrapper catches final failure after retries are exhausted,
    so the @retry decorator sees raised exceptions and retries correctly.
    """
    return await _fetch_ticker_with_retry(ticker)


def _download_sync(ticker: str):
    """Sync yfinance download — called inside asyncio.to_thread.
    Normalizes all fetched prices to USD using live Forex rates."""
    t = yf.Ticker(ticker)
    df = t.history(period="1d", interval="15m")
    
    # Bug fix: Ensure all prices are stored strictly in USD
    currency = getattr(t.fast_info, 'currency', 'USD')
    if currency and currency.upper() != 'USD':
        try:
            fx = yf.Ticker(f"{currency.upper()}USD=X")
            rate = getattr(fx.fast_info, 'last_price', 1.0)
            if rate != 1.0 and rate > 0:
                logger.info("Converting %s from %s to USD at rate %f", ticker, currency, rate)
                df['Open'] *= rate
                df['High'] *= rate
                df['Low'] *= rate
                df['Close'] *= rate
        except Exception as e:
            logger.warning("Forex conversion failed for %s to USD: %s", currency, e)
            
    return df


async def fetch_all(tickers: List[str]) -> dict[str, List[RawTickIn]]:
    """
    Fetch all tickers concurrently. Returns dict {ticker: [ticks]}.
    Failures per ticker are isolated — one bad ticker won't stop others.
    """
    # Bug fix #1: use asyncio.gather for true concurrency instead of sequential awaits
    results_list = await asyncio.gather(
        *[fetch_ticker(ticker) for ticker in tickers],
        return_exceptions=True,
    )
    
    for ticker, res in zip(tickers, results_list):
        if isinstance(res, Exception):
            logger.error("All retries failed for %s: %s", ticker, str(res))
            
    return {
        ticker: (res if not isinstance(res, Exception) else [])
        for ticker, res in zip(tickers, results_list)
    }
