"""
tests/test_stats_engine.py — Unit tests for statistical analysis.
No DB, no LLM — pure math. Shows you understand what your code does.
"""
import pytest
from app.analysis.stats_engine import analyse_ticker, compute_rsi


# ── RSI Tests ─────────────────────────────────────────────────────────────────

def test_rsi_overbought():
    # Mostly rising prices with tiny dips so RSI computes (non-zero loss required)
    import pandas as pd
    closes = [100, 102, 101, 104, 103, 106, 105, 108, 107, 110,
              109, 112, 111, 114, 113, 116, 115, 118, 117, 120]
    rsi = compute_rsi(pd.Series([float(c) for c in closes]))
    assert rsi > 60, f"Expected RSI > 60 for mostly-rising prices, got {rsi}"


def test_rsi_oversold():
    # Steadily falling prices → low RSI
    closes = [float(200 - i * 2) for i in range(20)]
    rsi = compute_rsi(__import__("pandas").Series(closes))
    assert rsi < 30, f"Expected RSI < 30 for falling prices, got {rsi}"


def test_rsi_insufficient_data():
    # Not enough data → returns neutral 50.0
    closes = [100.0, 101.0, 99.0]
    import pandas as pd
    rsi = compute_rsi(pd.Series(closes))
    assert rsi == 50.0


# ── analyse_ticker Tests ──────────────────────────────────────────────────────

def test_insufficient_bars_returns_normal():
    result = analyse_ticker("TEST", [100.0, 101.0], [1000, 1000])
    assert result.has_anomaly is False
    assert result.signal_type == "normal"
    assert "Insufficient" in result.description


def test_price_spike_detected():
    # Normal prices for 18 bars, then a massive spike
    closes = [100.0] * 18 + [100.0, 150.0]  # 50% spike on last bar
    volumes = [1_000_000] * 20
    result = analyse_ticker("SPIKE", closes, volumes)
    assert result.has_anomaly is True
    assert result.signal_type == "anomaly"
    assert result.zscore is not None and result.zscore > 2.0


def test_stable_prices_no_anomaly():
    # Very stable price — no anomaly expected
    import random
    random.seed(42)
    closes = [100.0 + random.uniform(-0.1, 0.1) for _ in range(20)]
    volumes = [1_000_000] * 20
    result = analyse_ticker("STABLE", closes, volumes)
    assert result.has_anomaly is False


def test_volume_spike_detected():
    closes = [100.0] * 20
    volumes = [1_000_000] * 19 + [10_000_000]  # 10x volume spike
    result = analyse_ticker("VOLSPIKE", closes, volumes)
    # Volume spike should be flagged
    assert result.has_anomaly is True


def test_price_change_pct_calculated():
    closes = [100.0] * 19 + [105.0]
    volumes = [1_000_000] * 20
    result = analyse_ticker("TEST", closes, volumes)
    assert result.price_change_pct is not None
    assert abs(result.price_change_pct - 0.05) < 0.001  # 5% change
