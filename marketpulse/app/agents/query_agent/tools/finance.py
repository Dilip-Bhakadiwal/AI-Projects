"""
Financial Data Tools
"""
import json
import structlog
import yfinance as yf
from langchain_core.tools import tool

logger = structlog.get_logger(__name__)

@tool(response_format="content_and_artifact")
def get_financial_data(ticker: str, include_widget: bool = False) -> tuple[str, dict]:
    """
    Get live financial data, fundamentals, and recent quotes for any stock (including Indian NSE/BSE and US stocks).
    Use this when the user asks for the current price, market cap, P/E ratio, or live stock information.
    Args:
        ticker: The stock symbol or company name (e.g., 'AAPL', 'ZOMATO', 'SWIGGY', 'COLPAL.NS', '005930.KS')
        include_widget: MUST be True when user says 'show card', 'show widget', 'show chart', 'full report', or 'show me a card for X'. Defaults to False for simple price questions.
    """
    logger.info("tool_get_financial_data", ticker=ticker, widget_requested=include_widget)
    try:
        from app.services.stock_scraper import get_stock_snapshot_sync
        snapshot = get_stock_snapshot_sync(ticker)

        if not snapshot or snapshot.get("last_price", 0.0) == 0.0:
            return (
                f"TOOL_FAILURE: Could not retrieve live stock data for '{ticker}'. "
                f"INSTRUCTION: Do NOT call get_financial_data again. Either answer the user directly explaining that '{ticker}' is currently unavailable, OR call search_web EXACTLY ONCE to summarize the latest news/price from the web without calling any more tools.",
                {}
            )

        resolved_ticker = snapshot["ticker"]
        c_px = snapshot["last_price"]
        p_px = snapshot["previous_close"]
        diff = snapshot["change_val"]
        pct = snapshot["change_pct"]
        currency = snapshot["currency"]
        name = snapshot["company_name"]

        widget_json = {
            "ticker": resolved_ticker,
            "name": name,
            "price": f"{c_px:,.2f}",
            "currency": currency,
            "change_pct": f"{pct:+.2f}%",
            "change_val": f"{diff:+.2f}",
            "open": str(snapshot.get("open_price") or "N/A"),
            "high": str(snapshot.get("day_high") or "N/A"),
            "low": str(snapshot.get("day_low") or "N/A"),
            "mkt_cap": str(snapshot.get("market_cap") or "N/A"),
            "pe": str(snapshot.get("pe_ratio") or "N/A"),
            "div": f"{snapshot.get('dividend_yield', 0):.2f}%" if snapshot.get("dividend_yield") else "N/A",
            "high_52": str(snapshot.get("high_52week") or "N/A"),
            "low_52": str(snapshot.get("low_52week") or "N/A"),
        }

        if include_widget:
            return (
                f"Live stock data for requested query '{ticker}' (Symbol: {resolved_ticker} | Company: {name}):\n"
                f"- Current Price: {c_px:,.2f} {currency}\n"
                f"- Change: {diff:+.2f} ({pct:+.2f}%)\n"
                f"- Exchange: {snapshot.get('exchange')}\n"
                f"Successfully displayed widget to user.\n\n"
                f"(Agent Instruction: The stock price for '{ticker}' is {c_px:,.2f} {currency} under ticker symbol {resolved_ticker}. Answer the user directly with this price.)",
                widget_json,
            )
        else:
            return (
                f"Live stock data for requested query '{ticker}' (Symbol: {resolved_ticker} | Company: {name}):\n"
                f"- Current Price: {c_px:,.2f} {currency}\n"
                f"- Change: {diff:+.2f} ({pct:+.2f}%)\n"
                f"- Exchange: {snapshot.get('exchange')}\n"
                f"- Market Cap: {snapshot.get('market_cap')}\n"
                f"- P/E Ratio: {snapshot.get('pe_ratio')}\n\n"
                f"(Agent Instruction: The stock price for '{ticker}' is {c_px:,.2f} {currency} under ticker symbol {resolved_ticker}. Answer the user directly with this price.)",
                {},
            )
    except Exception as e:
        return (json.dumps({"error": f"Failed to fetch financial data for {ticker}: {str(e)}"}), {})
