# Top 20 DSA-Level Database Query Algorithms & SQL Solutions

This document presents the **Top 20 Data Structures & Algorithms (DSA)** level database query problems, SQL window function patterns, and algorithmic solutions used in high-frequency trading data pipelines, analytical processing, and software engineering interviews.

---

## Catalog of Queries

### 1. Nth Highest Stock Price / Salary (`DENSE_RANK`)
- **Problem**: Find the $N$-th highest price per ticker without skipping ranks on ties.
- **Complexity**: Time: $O(K \log K)$ per partition, Space: $O(K)$
- **SQL Solution**:
```sql
WITH RankedPrices AS (
    SELECT ticker, last_price, last_updated,
           DENSE_RANK() OVER (PARTITION BY ticker ORDER BY last_price DESC) AS rnk
    FROM stock_snapshots
)
SELECT ticker, last_price, last_updated
FROM RankedPrices
WHERE rnk = :N;
```

---

### 2. Simple Moving Average (20-Bar Sliding Window)
- **Problem**: Calculate the 20-period rolling average price for time-series streams.
- **Complexity**: Time: $O(N)$, Space: $O(W)$ (where $W$ is window length)
- **SQL Solution**:
```sql
SELECT ticker, last_updated, last_price,
       AVG(last_price) OVER (
           PARTITION BY ticker 
           ORDER BY last_updated 
           ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
       ) AS sma_20
FROM stock_snapshots;
```

---

### 3. Gaps and Islands (Longest Consecutive Bullish Streak)
- **Problem**: Find the longest consecutive streak of bars where price increased per ticker.
- **Complexity**: Time: $O(N \log N)$, Space: $O(N)$
- **SQL Solution**:
```sql
WITH PriceChanges AS (
    SELECT ticker, last_updated, last_price,
           CASE WHEN last_price > LAG(last_price) OVER (PARTITION BY ticker ORDER BY last_updated) THEN 1 ELSE 0 END AS is_up,
           ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY last_updated) AS rn
    FROM stock_snapshots
),
GroupedStreaks AS (
    SELECT ticker, is_up,
           rn - ROW_NUMBER() OVER (PARTITION BY ticker, is_up ORDER BY last_updated) AS streak_grp
    FROM PriceChanges
    WHERE is_up = 1
)
SELECT ticker, COUNT(*) AS max_consecutive_up_bars
FROM GroupedStreaks
GROUP BY ticker, streak_grp
ORDER BY max_consecutive_up_bars DESC;
```

---

### 4. Rolling Z-Score Anomaly Detection
- **Problem**: Flag statistical price anomalies where $|Z| > 2.0$ standard deviations from the 20-bar mean.
- **Complexity**: Time: $O(N)$, Space: $O(N)$
- **SQL Solution**:
```sql
WITH RollingStats AS (
    SELECT ticker, last_updated, last_price,
           AVG(last_price) OVER w AS mean_price,
           STDDEV(last_price) OVER w AS std_price
    FROM stock_snapshots
    WINDOW w AS (PARTITION BY ticker ORDER BY last_updated ROWS BETWEEN 19 PRECEDING AND 1 PRECEDING)
)
SELECT ticker, last_updated, last_price,
       (last_price - mean_price) / NULLIF(std_price, 0) AS z_score,
       CASE WHEN ABS((last_price - mean_price) / NULLIF(std_price, 0)) > 2.0 THEN TRUE ELSE FALSE END AS is_anomaly
FROM RollingStats;
```

---

### 5. Top K Stocks Per Exchange / Category
- **Problem**: Retrieve top $K$ highest-volume stocks within each exchange.
- **Complexity**: Time: $O(N \log K)$, Space: $O(N)$
- **SQL Solution**:
```sql
WITH VolumeRanked AS (
    SELECT ticker, exchange, volume, last_price,
           ROW_NUMBER() OVER (PARTITION BY exchange ORDER BY volume DESC) AS pos
    FROM stock_snapshots
)
SELECT exchange, pos AS rank, ticker, volume, last_price
FROM VolumeRanked
WHERE pos <= :K;
```

---

### 6. Cumulative Running Total Volume
- **Problem**: Calculate running sum of traded volume throughout the day.
- **Complexity**: Time: $O(N)$, Space: $O(N)$
- **SQL Solution**:
```sql
SELECT ticker, last_updated, volume,
       SUM(volume) OVER (
           PARTITION BY ticker 
           ORDER BY last_updated 
           ROWS UNBOUNDED PRECEDING
       ) AS cumulative_volume
FROM stock_snapshots;
```

---

### 7. Relative Strength Index (RSI 14-Period)
- **Problem**: Compute RSI momentum indicator over 14 price changes.
- **Complexity**: Time: $O(N)$, Space: $O(N)$
- **Formula**: $RSI = 100 - \frac{100}{1 + \frac{\text{Avg Gain}}{\text{Avg Loss}}}$

---

### 8. Time-Series Gap Detection (Missing Feed Intervals)
- **Problem**: Detect gaps where market data was missing for >15 minutes.
- **SQL Solution**:
```sql
WITH Timediff AS (
    SELECT ticker, last_updated,
           LAG(last_updated) OVER (PARTITION BY ticker ORDER BY last_updated) AS prev_time
    FROM stock_snapshots
)
SELECT ticker, prev_time AS gap_start, last_updated AS gap_end,
       EXTRACT(EPOCH FROM (last_updated - prev_time)) / 60 AS gap_minutes
FROM Timediff
WHERE EXTRACT(EPOCH FROM (last_updated - prev_time)) > 900;
```

---

### 9. Bar-Over-Bar Percentage Return
- **Problem**: Compute discrete return $(P_t - P_{t-1}) / P_{t-1}$ per interval.
- **SQL Solution**:
```sql
SELECT ticker, last_updated, last_price,
       (last_price - LAG(last_price) OVER (PARTITION BY ticker ORDER BY last_updated))
       / NULLIF(LAG(last_price) OVER (PARTITION BY ticker ORDER BY last_updated), 0) AS return_pct
FROM stock_snapshots;
```

---

### 10. Local Extrema Peak and Trough Detection
- **Problem**: Identify local price peaks where $P_t > P_{t-1}$ and $P_t > P_{t+1}$.
- **SQL Solution**:
```sql
WITH Extrema AS (
    SELECT ticker, last_updated, last_price,
           LAG(last_price) OVER w AS prev_price,
           LEAD(last_price) OVER w AS next_price
    FROM stock_snapshots
    WINDOW w AS (PARTITION BY ticker ORDER BY last_updated)
)
SELECT ticker, last_updated, last_price, 'PEAK' AS point_type
FROM Extrema
WHERE last_price > prev_price AND last_price > next_price;
```

---

### 11. Conditional Aggregation Performance Pivot
- **Problem**: Pivot quarterly average price by ticker into separate columns.
- **SQL Solution**:
```sql
SELECT ticker,
       AVG(CASE WHEN EXTRACT(QUARTER FROM last_updated) = 1 THEN last_price END) AS Q1_avg,
       AVG(CASE WHEN EXTRACT(QUARTER FROM last_updated) = 2 THEN last_price END) AS Q2_avg,
       AVG(CASE WHEN EXTRACT(QUARTER FROM last_updated) = 3 THEN last_price END) AS Q3_avg,
       AVG(CASE WHEN EXTRACT(QUARTER FROM last_updated) = 4 THEN last_price END) AS Q4_avg
FROM stock_snapshots
GROUP BY ticker;
```

---

### 12. Snapshot Deduplication (Retain Latest Record)
- **Problem**: Clean duplicates keeping only the single latest snapshot per ticker.
- **SQL Solution**:
```sql
DELETE FROM stock_snapshots
WHERE id NOT IN (
    SELECT id FROM (
        SELECT id, ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY last_updated DESC) as rn
        FROM stock_snapshots
    ) t WHERE t.rn = 1
);
```

---

### 13. Recursive CTE Sector Portfolio Tree Aggregation
- **Problem**: Aggregate total market cap across parent-child sector hierarchies.
- **SQL Solution**:
```sql
WITH RECURSIVE SectorTree AS (
    SELECT id, name, parent_id, id AS root_sector_id
    FROM sectors WHERE parent_id IS NULL
    UNION ALL
    SELECT s.id, s.name, s.parent_id, st.root_sector_id
    FROM sectors s
    INNER JOIN SectorTree st ON s.parent_id = st.id
)
SELECT st.root_sector_id, SUM(sp.market_cap) AS total_sector_val
FROM SectorTree st
JOIN stock_snapshots sp ON st.id = sp.sector_id
GROUP BY st.root_sector_id;
```

---

### 14. Trading Halt Window Overlap Check
- **Problem**: Detect whether two scheduled trading halt windows overlap.
- **Condition**: `(StartA <= EndB) AND (EndA >= StartB)`

---

### 15. Continuous Median and 95th Percentile Price
- **Problem**: Calculate 50th (median) and 95th percentile price per ticker.
- **SQL Solution**:
```sql
SELECT ticker,
       PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY last_price) AS median_price,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY last_price) AS p95_price
FROM stock_snapshots
GROUP BY ticker;
```

---

### 16. Stale Feed Zero-Variance Island Detector
- **Problem**: Detect tickers where price remained identical for $\ge 5$ updates.
- **Algorithm**: Group consecutive equal prices and count streak length.

---

### 17. Volume Weighted Average Price (VWAP)
- **Problem**: Compute $\frac{\sum (P_i \times V_i)}{\sum V_i}$ for intraday trading session.
- **SQL Solution**:
```sql
SELECT ticker, last_updated,
       SUM(last_price * volume) OVER w / NULLIF(SUM(volume) OVER w, 0) AS vwap
FROM stock_snapshots
WINDOW w AS (PARTITION BY ticker ORDER BY last_updated ROWS UNBOUNDED PRECEDING);
```

---

### 18. Session Open & Close Boundaries (`FIRST_VALUE` / `LAST_VALUE`)
- **Problem**: Get session opening and closing prices within window partitions.
- **SQL Solution**:
```sql
SELECT DISTINCT ticker,
       FIRST_VALUE(last_price) OVER w AS open_price,
       LAST_VALUE(last_price) OVER w AS close_price
FROM stock_snapshots
WINDOW w AS (
    PARTITION BY ticker ORDER BY last_updated 
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
);
```

---

### 19. V-Shape Momentum Reversal Pattern
- **Problem**: Detect rapid spike ($>+5\%$) immediately followed by sharp drop ($>-5\%$).
- **Algorithm**: Two-bar composite velocity check.

---

### 20. Pairwise Stock Co-Movement Correlation (Self-Join)
- **Problem**: Find pairs of stocks that experienced identical positive direction moves at the exact same timestamp.
- **SQL Solution**:
```sql
SELECT a.last_updated, a.ticker AS ticker1, b.ticker AS ticker2,
       a.change_pct AS move1, b.change_pct AS move2
FROM stock_snapshots a
JOIN stock_snapshots b 
  ON a.last_updated = b.last_updated 
 AND a.ticker < b.ticker
WHERE a.change_pct > 0.03 AND b.change_pct > 0.03;
```
