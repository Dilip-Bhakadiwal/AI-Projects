import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import engine
from sqlalchemy import text

async def main():
    async with engine.begin() as conn:
        print("Dropping raw_ticks...")
        await conn.execute(text("DROP TABLE IF EXISTS raw_ticks CASCADE;"))
        print("Dropping processed_signals...")
        await conn.execute(text("DROP TABLE IF EXISTS processed_signals CASCADE;"))
        print("Dropping agent_logs...")
        await conn.execute(text("DROP TABLE IF EXISTS agent_logs CASCADE;"))
        print("Dropping user_notes...")
        await conn.execute(text("DROP TABLE IF EXISTS user_notes CASCADE;"))

    print("Tables dropped successfully. Only ticker_configs remains.")

if __name__ == "__main__":
    asyncio.run(main())
