# Stock Data Scraper

A production-ready, 100% free/open-source stock data fetcher that works for **any exchange** — NSE, BSE, NYSE, NASDAQ, and more. No API keys, no trials.

## Features

- **Any ticker or company name** — resolves "swiggy", "COLPAL.NS", "Apple" to the correct listed symbol
- **Multi-source resilience** — Yahoo Finance → India adapter → Stooq (fallback chain per exchange)
- **Field-level merging** — picks the best value for each field across all sources
- **Pydantic validation** — strict schema enforcement; never silently returns bad data
- **Short TTL cache** — 30s for prices, 6h for ticker resolution
- **Handles company renames** — e.g. Zomato → Eternal Ltd (via Screener.in)

## Quick Start

```powershell
# Activate the virtual environment
& "C:\Users\Dilip\Desktop\project\env\Scripts\python.exe" scraper.py AAPL
& "C:\Users\Dilip\Desktop\project\env\Scripts\python.exe" scraper.py zomato
& "C:\Users\Dilip\Desktop\project\env\Scripts\python.exe" scraper.py "adani enterprises"
& "C:\Users\Dilip\Desktop\project\env\Scripts\python.exe" scraper.py SWIGGY.NS COLPAL.NS INFY.NS
```

## Programmatic Usage

```python
import sys
sys.path.insert(0, r'path\to\web scapler')
from scraper import fetch_stock

result = fetch_stock("ZOMATO")   # or "zomato", "ZOMATO.NS"
print(result["last_price"])
print(result["name"])
print(result["pe_ratio"])
```

## Output Fields

| Field              | Type    | Notes                            |
|--------------------|---------|----------------------------------|
| `ticker`           | str     | Exchange-qualified symbol        |
| `name`             | str     | Company name                     |
| `last_price`       | float   | Latest traded price              |
| `change`           | float?  | Price change from prev close     |
| `pct_change`       | float?  | % change from prev close         |
| `volume`           | int?    | Today's traded volume            |
| `market_cap`       | float?  | Market capitalisation (raw)      |
| `pe_ratio`         | float?  | Trailing P/E                     |
| `div_yield`        | float?  | Dividend yield (%)               |
| `source`           | str     | Which adapter(s) provided data   |
| `field_sources`    | dict    | Per-field source tracking        |
| `confidence`       | str     | "exact" or "fuzzy"               |
| `resolved_exchange`| str     | e.g. "NSE", "NASDAQ"             |

## Architecture (7 Stages)

```
User Query
    │
    ▼
[1] normalizer.py     — strip noise, preserve qualified tickers
    │
    ▼
[2] resolver.py       — Yahoo search + Screener.in + NSE autocomplete
    │                   Screener handles renamed companies (Zomato→Eternal)
    ▼
[3] router.py         — exchange-based adapter priority table
    │
    ▼
[4] adapters/
    ├── yahoo.py      — yfinance fast_info + direct chart endpoint
    ├── india.py      — NSE/BSE stocks; Screener.in ticker lookup
    ├── nse.py        — NSE India direct API (when accessible)
    └── stooq.py      — last-resort CSV fallback
    │
    ▼
[5] router.py         — field-level merger (best value per field)
    │
    ▼
[6] schema.py         — Pydantic StockRecord validation
    │
    ▼
[7] cache.py          — TTLCache (30s price, 6h resolver)
```

## Adapter Priority

| Exchange    | Order                          |
|-------------|--------------------------------|
| NSE / BSE   | yahoo → india → stooq          |
| NYSE/NASDAQ | yahoo → stooq                  |
| Other       | yahoo → india → stooq          |

## Run Tests

```powershell
& "C:\Users\Dilip\Desktop\project\env\Scripts\python.exe" tests/test_sanity.py
```

## Install Dependencies

```powershell
& "C:\Users\Dilip\Desktop\project\env\Scripts\pip.exe" install -r requirements.txt
```

## Known Limitations

- **NSE India direct API** — NSE now blocks automated requests with Cloudflare WAF. Yahoo Finance and Screener.in are used as reliable alternatives.
- **Stooq** — Does not reliably serve Indian stock symbols; used only as a last-resort fallback for US stocks.
- **Real-time data** — All sources provide ~15 min delayed data (this is standard for free sources).
- **P/E and Div Yield for recent IPOs** — May be null for newly listed companies with no earnings history.
