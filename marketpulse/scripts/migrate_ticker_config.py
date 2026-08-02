import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import engine
from sqlalchemy import text

async def main():
    async with engine.begin() as conn:
        print("Checking if columns exist...")
        try:
            # Try adding last_polled_at
            await conn.execute(text("ALTER TABLE ticker_configs ADD COLUMN last_polled_at TIMESTAMP WITH TIME ZONE NULL;"))
            print("Added last_polled_at.")
        except Exception as e:
            print(f"Skipping last_polled_at: {e}")
            
        try:
            # Try adding asset_type
            await conn.execute(text("ALTER TABLE ticker_configs ADD COLUMN asset_type VARCHAR(50) NULL;"))
            print("Added asset_type.")
        except Exception as e:
            print(f"Skipping asset_type: {e}")

        try:
            # Try adding currency
            await conn.execute(text("ALTER TABLE ticker_configs ADD COLUMN currency VARCHAR(10) NULL;"))
            print("Added currency.")
        except Exception as e:
            print(f"Skipping currency: {e}")

    print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(main())
