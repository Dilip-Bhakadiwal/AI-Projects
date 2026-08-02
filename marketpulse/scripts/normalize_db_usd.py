"""
Utility script to normalize all existing stocks in the PostgreSQL/SQLite database to USD ($).
Converts any foreign currency values (e.g., INR, EUR, GBP) using FX_RATES_TO_USD.
"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.stock import Stock
from app.services.stock_scraper import FX_RATES_TO_USD


async def normalize_database():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Stock))
        stocks = result.scalars().all()
        count = 0
        for st in stocks:
            if st.currency and st.currency.upper() != "USD":
                rate = FX_RATES_TO_USD.get(st.currency.upper(), 1.0)
                if rate > 0 and rate != 1.0:
                    if st.last_price:
                        st.last_price = round(st.last_price / rate, 2)
                    if st.change_val:
                        st.change_val = round(st.change_val / rate, 2)
                    if st.open_price:
                        st.open_price = round(st.open_price / rate, 2)
                    if st.previous_close:
                        st.previous_close = round(st.previous_close / rate, 2)
                    if st.day_high:
                        st.day_high = round(st.day_high / rate, 2)
                    if st.day_low:
                        st.day_low = round(st.day_low / rate, 2)
                    if st.high_52week:
                        st.high_52week = round(st.high_52week / rate, 2)
                    if st.low_52week:
                        st.low_52week = round(st.low_52week / rate, 2)
                    if st.market_cap:
                        st.market_cap = int(st.market_cap / rate)
                    st.currency = "USD"
                    count += 1
        await session.commit()
        print(f"Successfully normalized {count} existing database stocks to USD ($).")


if __name__ == "__main__":
    asyncio.run(normalize_database())
