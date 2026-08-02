# MarketPulse UI Tasks Checklist

- [x] Task 1: Set up `ui/` directory structure and copy assets (`bg-unsplash.jpg`, `DESIGN.md`, `screen.png`).
- [x] Task 2: Implement background image styling in `ui/index.html` with proper contrast fallback.
- [x] Task 3: Fix left side panel (`<aside>`) `.specular-highlight` hover effect positioning and margin removal.
- [x] Task 4: Sync updated UI code back to `extracted_stitch_design/code.html` for consistency.
- [x] Task 5: Verify WCAG accessibility, keyboard navigation, and responsive layout across breakpoints.
- [x] Task 6: Connect `web scapler` multi-adapter scraper to active `project` workspace (`marketpulse/app/services/stock_scraper.py`).
- [x] Task 7: Update `finance.py`, `db_write.py`, and `worker.py` to use `stock_scraper` bridge for Indian & US stocks.
- [x] Task 8: Fix LLM prompt and tool return formatting (`ETERNAL.NS` -> Zomato mapping) to prevent "I couldn't find data" hallucinations and search_web loops.
- [x] Task 9: Verify query agent response (`The stock price for Zomato is 302.45 INR.`) via automated test script.
