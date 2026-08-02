"""
marketpulse/tests/test_dsa_queries.py — Pytest suite for Top 20 DSA Database Queries.
"""
from datetime import datetime, timedelta, timezone
from marketpulse.tests.top_20_dsa_queries import (
    get_mock_dataset,
    query_1_nth_highest_price,
    query_2_simple_moving_average,
    query_3_gaps_and_islands_longest_streak,
    query_4_rolling_zscore_anomalies,
    query_5_top_k_items_per_category,
    query_6_cumulative_running_total,
    query_7_rsi_14,
    query_8_time_series_gap_detection,
    query_9_percentage_returns,
    query_10_peak_trough_detection,
    query_11_conditional_aggregation_pivot,
    query_12_deduplicate_latest,
    query_13_recursive_sector_aggregation,
    query_14_trading_halt_overlap,
    query_15_median_and_percentile,
    query_16_stale_feed_detector,
    query_17_volume_weighted_average_price,
    query_18_session_open_close,
    query_19_v_shape_reversal_pattern,
    query_20_pairwise_stock_correlation,
)


def test_top_20_dsa_queries():
    dataset = get_mock_dataset()

    # 1. Nth Highest Price
    assert query_1_nth_highest_price(dataset, "AAPL", 1) == 170.0
    assert query_1_nth_highest_price(dataset, "AAPL", 2) == 168.0

    # 2. Moving Average
    smas = query_2_simple_moving_average(dataset, "AAPL", 3)
    assert len(smas) == 10
    assert smas[0] == 150.0

    # 3. Gaps and Islands Streak
    streak = query_3_gaps_and_islands_longest_streak(dataset, "AAPL")
    assert streak >= 2

    # 4. Rolling Z-Score
    zscores = query_4_rolling_zscore_anomalies(dataset, "AAPL")
    assert len(zscores) == 10

    # 5. Top K Items
    top_k = query_5_top_k_items_per_category(dataset, 1)
    assert "NASDAQ" in top_k
    assert len(top_k["NASDAQ"]) == 1

    # 6. Cumulative Running Total
    cum_vols = query_6_cumulative_running_total(dataset, "AAPL")
    assert cum_vols[-1] == sum(r.volume for r in dataset if r.ticker == "AAPL")

    # 7. RSI 14
    rsi = query_7_rsi_14([100.0 + i for i in range(20)])
    assert rsi > 50.0

    # 8. Time Series Gaps
    gaps = query_8_time_series_gap_detection(dataset, 60)
    assert isinstance(gaps, list)

    # 9. Returns
    returns = query_9_percentage_returns(dataset, "AAPL")
    assert len(returns) == 10
    assert returns[0] == 0.0

    # 10. Peak & Trough
    extrema = query_10_peak_trough_detection(dataset, "AAPL")
    assert isinstance(extrema, list)

    # 11. Pivot
    pivots = query_11_conditional_aggregation_pivot(dataset)
    assert "AAPL" in pivots

    # 12. Deduplication
    deduped = query_12_deduplicate_latest(dataset)
    assert len(deduped) == 2

    # 13. Recursive Sector Tree
    tree = {1: None, 2: 1, 3: 2}
    vals = {1: 100.0, 2: 200.0, 3: 300.0}
    total_val = query_13_recursive_sector_aggregation(tree, vals, 1)
    assert total_val == 600.0

    # 14. Trading Halt Overlap
    t1 = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 1, 11, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 8, 1, 10, 30, tzinfo=timezone.utc)
    t4 = datetime(2026, 8, 1, 11, 30, tzinfo=timezone.utc)
    assert query_14_trading_halt_overlap((t1, t2), (t3, t4)) is True

    # 15. Median & Percentiles
    med, p95 = query_15_median_and_percentile([10, 20, 30, 40, 50], 0.95)
    assert med == 30
    assert p95 == 50

    # 16. Stale Feed
    is_stale = query_16_stale_feed_detector(dataset, "AAPL", 5)
    assert is_stale is False

    # 17. VWAP
    vwap = query_17_volume_weighted_average_price(dataset, "AAPL")
    assert vwap > 150.0

    # 18. Session Open/Close
    open_p, close_p = query_18_session_open_close(dataset, "AAPL")
    assert open_p == 150.0
    assert close_p == 168.0

    # 19. V-Shape Reversal
    reversals = query_19_v_shape_reversal_pattern(dataset, "TSLA")
    assert isinstance(reversals, list)

    # 20. Pairwise Stock Correlation
    pairs = query_20_pairwise_stock_correlation(dataset)
    assert len(pairs) > 0
