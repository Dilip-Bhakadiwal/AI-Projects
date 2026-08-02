"""
Unified Tools Export
"""
from app.agents.query_agent.tools.web import search_web, scrape_website
from app.agents.query_agent.tools.finance import get_financial_data
from app.agents.query_agent.tools.db_read import (
    view_portfolio_table,
    query_database
)
from app.agents.query_agent.tools.db_write import (
    add_stock,
    remove_stock,
    add_custom_stock,
    refresh_stock,
    refresh_all_stocks
)

QUERY_TOOLS = [
    search_web,
    scrape_website,
    get_financial_data,
    view_portfolio_table,
    query_database,
    add_stock,
    add_custom_stock,
    remove_stock,
    refresh_stock,
    refresh_all_stocks,
]
