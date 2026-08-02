"""
app/analysis/stats_engine.py — Statistical analysis engine.

Runs Z-score anomaly detection and RSI on price/volume data.
This is the lightweight, zero-cost first pass that decides whether
to invoke an expensive LLM call.
"""
import logging
import statistics
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Result of statistical analysis on a ticker's price/volume data."""
    ticker: str
    has_anomaly: bool = False
    confidence: float = 0.0
    signal_type: str = "normal"
    description: str = ""
    zscore: Optional[float] = None
    rsi: Optional[float] = None
    price_change_pct: Optional[float] = None
    last_close: float = 0.0


from typing import List, Optional, Sequence, Union


def compute_rsi(closes: Union[Sequence[float], List[float]], period: int = 14) -> float:
    """
    Compute the Relative Strength Index (RSI) for closing prices.
    Returns neutral 50.0 if insufficient data.
    """
    closes_list = list(closes) if closes is not None else []
    if len(closes_list) < period + 1:
        return 50.0

    deltas = [closes_list[i] - closes_list[i - 1] for i in range(1, len(closes_list))]
    recent_deltas = deltas[-(period):]

    gains = [d for d in recent_deltas if d > 0]
    losses = [-d for d in recent_deltas if d < 0]

    avg_gain = sum(gains) / period if gains else 0.0
    avg_loss = sum(losses) / period if losses else 0.0

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(rsi, 2)


def _compute_zscore(closes: Sequence[float], lookback: int = 20) -> Optional[float]:
    """Compute Z-score of the latest value vs the lookback window."""
    vals = [float(v) for v in closes]
    if len(vals) < 3:
        return None

    # Use historical window excluding the latest element
    window = vals[-(lookback + 1):-1] if len(vals) > lookback else vals[:-1]
    if len(window) < 2:
        return None

    mean = statistics.mean(window)
    stdev = statistics.stdev(window)

    if stdev == 0:
        if vals[-1] == mean:
            return 0.0
        # If std dev of history is zero and price jumped, return large Z-score outlier
        return 10.0 if vals[-1] > mean else -10.0

    return (vals[-1] - mean) / stdev


def _compute_volume_zscore(volumes: Sequence[int], lookback: int = 20) -> Optional[float]:
    """Compute Z-score of the latest volume vs historical volume window."""
    if not volumes or len(volumes) < 3:
        return None
    vols = [float(v) for v in volumes]
    window = vols[-(lookback + 1):-1] if len(vols) > lookback else vols[:-1]
    if len(window) < 2:
        return None

    mean = statistics.mean(window)
    stdev = statistics.stdev(window)

    if stdev == 0:
        if vols[-1] == mean:
            return 0.0
        return 10.0 if vols[-1] > mean else -10.0

    return (vols[-1] - mean) / stdev


def analyse_ticker(
    ticker: str,
    closes: List[float],
    volumes: List[int],
) -> AnalysisResult:
    """
    Run statistical analysis on a ticker.
    Returns AnalysisResult with anomaly detection results.

    Anomaly triggers:
    - |Z-score| > 2.0 (price is >2 standard deviations from mean)
    - RSI > 70 (overbought) or RSI < 30 (oversold)
    - Price change > ±5% in a single bar
    - Volume Z-score > 2.0 (unusual volume spike)
    """
    if not closes or len(closes) < 3:
        return AnalysisResult(
            ticker=ticker,
            has_anomaly=False,
            signal_type="normal",
            description="Insufficient data for analysis.",
            last_close=closes[-1] if closes else 0.0,
        )

    last_close = closes[-1]
    prev_close = closes[-2]
    price_change_pct = (last_close - prev_close) / prev_close if prev_close != 0 else 0.0

    zscore = _compute_zscore(closes)
    rsi = compute_rsi(closes)
    vol_zscore = _compute_volume_zscore(volumes) if volumes else None

    # Anomaly detection logic
    anomalies = []
    confidence = 0.0

    # Z-score anomaly
    if zscore is not None and abs(zscore) > 2.0:
        anomalies.append(f"Z-score of {zscore:.2f} indicates statistical outlier")
        confidence = max(confidence, min(abs(zscore) / 4.0, 1.0))

    # RSI anomaly
    if rsi is not None and rsi != 50.0:
        if rsi > 70:
            anomalies.append(f"RSI of {rsi:.1f} indicates overbought conditions")
            confidence = max(confidence, (rsi - 70) / 30.0)
        elif rsi < 30:
            anomalies.append(f"RSI of {rsi:.1f} indicates oversold conditions")
            confidence = max(confidence, (30 - rsi) / 30.0)

    # Large price move
    if abs(price_change_pct) > 0.05:
        direction = "up" if price_change_pct > 0 else "down"
        anomalies.append(f"Price moved {price_change_pct:+.2%} ({direction}) in last bar")
        confidence = max(confidence, min(abs(price_change_pct) / 0.10, 1.0))

    # Volume anomaly
    if vol_zscore is not None and abs(vol_zscore) > 2.0:
        anomalies.append(f"Volume Z-score of {vol_zscore:.2f} indicates unusual volume spike")
        confidence = max(confidence, min(abs(vol_zscore) / 4.0, 1.0))

    has_anomaly = len(anomalies) > 0

    if has_anomaly:
        signal_type = "anomaly"
        description = f"{ticker}: " + "; ".join(anomalies) + f". Last close: ${last_close:.2f}."
    else:
        signal_type = "normal"
        z_str = f"Z={zscore:.2f}" if zscore is not None else "Z=N/A"
        rsi_str = f"RSI={rsi:.1f}" if rsi is not None else "RSI=N/A"
        description = f"{ticker}: No anomaly detected ({z_str}, {rsi_str}). Last close: ${last_close:.2f}."

    result = AnalysisResult(
        ticker=ticker,
        has_anomaly=has_anomaly,
        confidence=round(confidence, 3),
        signal_type=signal_type,
        description=description,
        zscore=round(zscore, 4) if zscore is not None else None,
        rsi=round(rsi, 2) if rsi is not None else None,
        price_change_pct=round(price_change_pct, 6) if price_change_pct is not None else None,
        last_close=last_close,
    )

    logger.info(
        "Analysis for %s: anomaly=%s confidence=%.3f type=%s",
        ticker, has_anomaly, confidence, signal_type,
    )
    return result
