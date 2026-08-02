"""
tests/test_validator.py — Unit tests for Pydantic validation.
These run without DB or network — pure logic tests.
"""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from app.ingestion.validator import RawTickIn


def make_valid_tick(**overrides) -> dict:
    base = {
        "ticker": "AAPL",
        "timestamp": datetime.now(timezone.utc),
        "open": 150.0,
        "high": 155.0,
        "low": 149.0,
        "close": 153.0,
        "volume": 1_000_000,
    }
    base.update(overrides)
    return base


def test_valid_tick_passes():
    tick = RawTickIn(**make_valid_tick())
    assert tick.ticker == "AAPL"
    assert tick.close == 153.0


def test_negative_price_rejected():
    with pytest.raises(ValidationError):
        RawTickIn(**make_valid_tick(close=-5.0))


def test_zero_price_rejected():
    with pytest.raises(ValidationError):
        RawTickIn(**make_valid_tick(open=0.0))


def test_nan_price_rejected():
    import math
    with pytest.raises(ValidationError):
        RawTickIn(**make_valid_tick(close=float("nan")))


def test_high_less_than_low_rejected():
    with pytest.raises(ValidationError):
        RawTickIn(**make_valid_tick(high=140.0, low=149.0))


def test_negative_volume_rejected():
    with pytest.raises(ValidationError):
        RawTickIn(**make_valid_tick(volume=-100))


def test_ticker_uppercased_stored_as_given():
    # Ticker is stored as-is — uppercasing is done in fetcher, not validator
    tick = RawTickIn(**make_valid_tick(ticker="aapl"))
    assert tick.ticker == "aapl"  # validator doesn't uppercase
