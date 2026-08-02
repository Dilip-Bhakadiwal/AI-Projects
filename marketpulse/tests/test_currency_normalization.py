"""
Unit test for Automatic USD Currency Normalization of stock prices and valuations.
Verifies that Indian INR and other foreign currency stocks are converted to USD ($)
while keeping unitless percentage metrics and volume invariant.
"""
from datetime import datetime, timezone
from app.services.stock_scraper import normalize_snapshot_to_usd, FX_RATES_TO_USD


def test_inr_to_usd_normalization():
    inr_snapshot = {
        "ticker": "ADANIENT.NS",
        "company_name": "Adani Enterprises",
        "last_price": 3009.50,
        "change_val": -40.50,
        "change_pct": -1.33,
        "volume": 866401,
        "open_price": 3050.0,
        "previous_close": 3050.0,
        "day_high": 3060.0,
        "day_low": 3000.0,
        "market_cap": 4074028164700,
        "currency": "INR",
        "pe_ratio": 35.2,
        "high_52week": 3400.0,
        "low_52week": 2100.0,
        "dividend_yield": 0.5,
        "eps": 85.4,
        "exchange": "NSE",
        "last_updated": datetime.now(timezone.utc),
    }

    normalized = normalize_snapshot_to_usd(inr_snapshot)

    assert normalized["currency"] == "USD"
    # INR rate is 83.50 -> 3009.50 / 83.50 = 36.04
    assert normalized["last_price"] == round(3009.50 / FX_RATES_TO_USD["INR"], 2)
    assert normalized["change_val"] == round(-40.50 / FX_RATES_TO_USD["INR"], 2)
    # Unitless percentage fields and volume must NOT change
    assert normalized["change_pct"] == -1.33
    assert normalized["volume"] == 866401
    assert normalized["pe_ratio"] == 35.2
    assert normalized["dividend_yield"] == 0.5
    # Exchange must be preserved
    assert normalized["exchange"] == "NSE"


def test_usd_unchanged():
    usd_snapshot = {
        "ticker": "AMD",
        "company_name": "Advanced Micro Devices",
        "last_price": 476.15,
        "currency": "USD",
        "change_pct": -4.64,
    }

    normalized = normalize_snapshot_to_usd(usd_snapshot)

    assert normalized["currency"] == "USD"
    assert normalized["last_price"] == 476.15
    assert normalized["change_pct"] == -4.64
