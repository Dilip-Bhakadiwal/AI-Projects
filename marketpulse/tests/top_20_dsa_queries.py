"""
marketpulse/tests/top_20_dsa_queries.py — Top 20 DSA-Level Database Queries & Algorithms Engine.

Demonstrates all 20 DSA query algorithms in Python using memory fixtures.
"""
import math
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class StockRecord:
    id: int
    ticker: str
    exchange: str
    last_price: float
    volume: int
    last_updated: datetime
    sector_id: int = 1


def get_mock_dataset() -> List[StockRecord]:
    base_time = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
    records = []
    
    # AAPL series
    aapl_prices = [150.0, 152.0, 151.0, 155.0, 158.0, 162.0, 160.0, 165.0, 170.0, 168.0]
    aapl_vols = [1000, 1200, 1100, 2500, 3000, 1500, 1400, 4000, 5000, 2000]
    for i, (p, v) in enumerate(zip(aapl_prices, aapl_vols)):
        records.append(StockRecord(i+1, "AAPL", "NASDAQ", p, v, base_time + timedelta(minutes=i*15)))

    # TSLA series
    tsla_prices = [200.0, 195.0, 190.0, 185.0, 180.0, 175.0, 170.0, 210.0, 165.0, 160.0]
    tsla_vols = [3000, 3100, 3200, 3300, 3400, 3500, 3600, 9500, 2000, 1900]
    for i, (p, v) in enumerate(zip(tsla_prices, tsla_vols)):
        records.append(StockRecord(100+i+1, "TSLA", "NASDAQ", p, v, base_time + timedelta(minutes=i*15)))
        
    return records


# ── Top 20 DSA Query Implementations ─────────────────────────────────────────

def query_1_nth_highest_price(records: List[StockRecord], ticker: str, n: int) -> Optional[float]:
    """1. Nth Highest Price (Dense Rank)."""
    prices = sorted(list(set(r.last_price for r in records if r.ticker == ticker)), reverse=True)
    return prices[n - 1] if 1 <= n <= len(prices) else None


def query_2_simple_moving_average(records: List[StockRecord], ticker: str, window: int = 5) -> List[float]:
    """2. Simple Moving Average (SMA)."""
    t_recs = sorted([r for r in records if r.ticker == ticker], key=lambda r: r.last_updated)
    prices = [r.last_price for r in t_recs]
    smas = []
    for i in range(len(prices)):
        sub = prices[max(0, i - window + 1):i + 1]
        smas.append(round(sum(sub) / len(sub), 2))
    return smas


def query_3_gaps_and_islands_longest_streak(records: List[StockRecord], ticker: str) -> int:
    """3. Gaps and Islands (Longest Consecutive Price Increase Streak)."""
    t_recs = sorted([r for r in records if r.ticker == ticker], key=lambda r: r.last_updated)
    max_streak = 0
    current = 0
    for i in range(1, len(t_recs)):
        if t_recs[i].last_price > t_recs[i - 1].last_price:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def query_4_rolling_zscore_anomalies(records: List[StockRecord], ticker: str) -> List[Tuple[datetime, float, bool]]:
    """4. Rolling Z-Score Anomaly Detection."""
    t_recs = sorted([r for r in records if r.ticker == ticker], key=lambda r: r.last_updated)
    res = []
    for i in range(len(t_recs)):
        if i < 2:
            res.append((t_recs[i].last_updated, 0.0, False))
            continue
        history = [r.last_price for r in t_recs[:i]]
        mean = statistics.mean(history)
        stdev = statistics.stdev(history) if len(history) > 1 else 0.0
        z = (t_recs[i].last_price - mean) / stdev if stdev > 0 else 0.0
        res.append((t_recs[i].last_updated, round(z, 2), abs(z) > 2.0))
    return res


def query_5_top_k_items_per_category(records: List[StockRecord], k: int = 2) -> Dict[str, List[StockRecord]]:
    """5. Top K Items Per Category (Exchange)."""
    by_ex: Dict[str, List[StockRecord]] = {}
    for r in records:
        by_ex.setdefault(r.exchange, []).append(r)
    res = {}
    for ex, recs in by_ex.items():
        res[ex] = sorted(recs, key=lambda r: r.volume, reverse=True)[:k]
    return res


def query_6_cumulative_running_total(records: List[StockRecord], ticker: str) -> List[int]:
    """6. Cumulative Running Total Volume."""
    t_recs = sorted([r for r in records if r.ticker == ticker], key=lambda r: r.last_updated)
    running = 0
    totals = []
    for r in t_recs:
        running += r.volume
        totals.append(running)
    return totals


def query_7_rsi_14(prices: List[float], period: int = 14) -> float:
    """7. Relative Strength Index (RSI)."""
    if len(prices) < period + 1:
        return 50.0
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [d for d in deltas[-period:] if d > 0]
    losses = [-d for d in deltas[-period:] if d < 0]
    avg_gain = sum(gains) / period if gains else 0.0
    avg_loss = sum(losses) / period if losses else 0.0
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def query_8_time_series_gap_detection(records: List[StockRecord], max_gap_minutes: int = 15) -> List[Tuple[datetime, datetime]]:
    """8. Time-Series Gap Detection."""
    t_recs = sorted(records, key=lambda r: r.last_updated)
    gaps = []
    for i in range(1, len(t_recs)):
        diff = (t_recs[i].last_updated - t_recs[i - 1].last_updated).total_seconds() / 60.0
        if diff > max_gap_minutes:
            gaps.append((t_recs[i - 1].last_updated, t_recs[i].last_updated))
    return gaps


def query_9_percentage_returns(records: List[StockRecord], ticker: str) -> List[float]:
    """9. Bar-Over-Bar Percentage Returns."""
    t_recs = sorted([r for r in records if r.ticker == ticker], key=lambda r: r.last_updated)
    returns = [0.0]
    for i in range(1, len(t_recs)):
        prev = t_recs[i - 1].last_price
        curr = t_recs[i].last_price
        ret = (curr - prev) / prev if prev != 0 else 0.0
        returns.append(round(ret, 4))
    return returns


def query_10_peak_trough_detection(records: List[StockRecord], ticker: str) -> List[Tuple[datetime, str]]:
    """10. Peak & Trough Extrema Detection."""
    t_recs = sorted([r for r in records if r.ticker == ticker], key=lambda r: r.last_updated)
    extrema = []
    for i in range(1, len(t_recs) - 1):
        prev_p = t_recs[i - 1].last_price
        curr_p = t_recs[i].last_price
        next_p = t_recs[i + 1].last_price
        if curr_p > prev_p and curr_p > next_p:
            extrema.append((t_recs[i].last_updated, "PEAK"))
        elif curr_p < prev_p and curr_p < next_p:
            extrema.append((t_recs[i].last_updated, "TROUGH"))
    return extrema


def query_11_conditional_aggregation_pivot(records: List[StockRecord]) -> Dict[str, Dict[str, float]]:
    """11. Conditional Aggregation Pivot by Ticker."""
    res: Dict[str, Dict[str, float]] = {}
    for r in records:
        if r.ticker not in res:
            res[r.ticker] = {"min_price": r.last_price, "max_price": r.last_price, "avg_price": r.last_price}
        else:
            res[r.ticker]["min_price"] = min(res[r.ticker]["min_price"], r.last_price)
            res[r.ticker]["max_price"] = max(res[r.ticker]["max_price"], r.last_price)
    return res


def query_12_deduplicate_latest(records: List[StockRecord]) -> List[StockRecord]:
    """12. Deduplication Retaining Latest Record."""
    latest: Dict[str, StockRecord] = {}
    for r in records:
        if r.ticker not in latest or r.last_updated > latest[r.ticker].last_updated:
            latest[r.ticker] = r
    return list(latest.values())


def query_13_recursive_sector_aggregation(hierarchy: Dict[int, Optional[int]], values: Dict[int, float], root_id: int) -> float:
    """13. Hierarchical Recursive Tree Aggregation."""
    total = values.get(root_id, 0.0)
    children = [node for node, parent in hierarchy.items() if parent == root_id]
    for child in children:
        total += query_13_recursive_sector_aggregation(hierarchy, values, child)
    return total


def query_14_trading_halt_overlap(window1: Tuple[datetime, datetime], window2: Tuple[datetime, datetime]) -> bool:
    """14. Trading Halt Window Overlap Check."""
    start1, end1 = window1
    start2, end2 = window2
    return start1 <= end2 and end1 >= start2


def query_15_median_and_percentile(prices: List[float], percentile: float = 0.95) -> Tuple[float, float]:
    """15. Continuous Median and Percentile Calculation."""
    if not prices:
        return 0.0, 0.0
    sorted_p = sorted(prices)
    med = statistics.median(sorted_p)
    idx = int(math.ceil(percentile * len(sorted_p))) - 1
    p_val = sorted_p[max(0, min(idx, len(sorted_p) - 1))]
    return med, p_val


def query_16_stale_feed_detector(records: List[StockRecord], ticker: str, min_stale_count: int = 3) -> bool:
    """16. Stale Feed Zero-Variance Island Detector."""
    t_recs = sorted([r for r in records if r.ticker == ticker], key=lambda r: r.last_updated)
    if len(t_recs) < min_stale_count:
        return False
    streak = 1
    for i in range(1, len(t_recs)):
        if t_recs[i].last_price == t_recs[i - 1].last_price:
            streak += 1
            if streak >= min_stale_count:
                return True
        else:
            streak = 1
    return False


def query_17_volume_weighted_average_price(records: List[StockRecord], ticker: str) -> float:
    """17. Volume Weighted Average Price (VWAP)."""
    t_recs = [r for r in records if r.ticker == ticker]
    total_pv = sum(r.last_price * r.volume for r in t_recs)
    total_vol = sum(r.volume for r in t_recs)
    return round(total_pv / total_vol, 2) if total_vol > 0 else 0.0


def query_18_session_open_close(records: List[StockRecord], ticker: str) -> Tuple[float, float]:
    """18. Session Open and Close Extraction."""
    t_recs = sorted([r for r in records if r.ticker == ticker], key=lambda r: r.last_updated)
    if not t_recs:
        return 0.0, 0.0
    return t_recs[0].last_price, t_recs[-1].last_price


def query_19_v_shape_reversal_pattern(records: List[StockRecord], ticker: str) -> List[datetime]:
    """19. V-Shape Price Reversal Pattern Detection."""
    t_recs = sorted([r for r in records if r.ticker == ticker], key=lambda r: r.last_updated)
    reversals = []
    for i in range(1, len(t_recs) - 1):
        prev = t_recs[i - 1].last_price
        curr = t_recs[i].last_price
        nxt = t_recs[i + 1].last_price
        if (curr - prev) / prev > 0.05 and (nxt - curr) / curr < -0.05:
            reversals.append(t_recs[i].last_updated)
    return reversals


def query_20_pairwise_stock_correlation(records: List[StockRecord]) -> List[Tuple[str, str, datetime]]:
    """20. Pairwise Stock Co-Movement Alignment (Self-Join)."""
    by_time: Dict[datetime, List[StockRecord]] = {}
    for r in records:
        by_time.setdefault(r.last_updated, []).append(r)
    pairs = []
    for dt, recs in by_time.items():
        if len(recs) >= 2:
            for i in range(len(recs)):
                for j in range(i + 1, len(recs)):
                    pairs.append((recs[i].ticker, recs[j].ticker, dt))
    return pairs


if __name__ == "__main__":
    dataset = get_mock_dataset()
    print("=== MARKETPULSE TOP 20 DSA DATABASE QUERIES ENGINE ===")
    print(f"Dataset loaded: {len(dataset)} records")
    print(f"1. AAPL 2nd Highest Price: {query_1_nth_highest_price(dataset, 'AAPL', 2)}")
    print(f"2. AAPL SMA (5-bar): {query_2_simple_moving_average(dataset, 'AAPL', 5)}")
    print(f"3. AAPL Longest Streak: {query_3_gaps_and_islands_longest_streak(dataset, 'AAPL')}")
    print(f"5. Top 1 Volume per Exchange: {query_5_top_k_items_per_category(dataset, 1)}")
    print(f"17. AAPL VWAP: ${query_17_volume_weighted_average_price(dataset, 'AAPL')}")
    print(f"18. AAPL Open/Close: {query_18_session_open_close(dataset, 'AAPL')}")
    print("All 20 queries initialized and ready.")
