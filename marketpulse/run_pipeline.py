"""
run_pipeline.py — One-shot pipeline runner for testing.
Run: python run_pipeline.py
"""
import asyncio
import logging
from app.database import init_db
from app.worker import run_pipeline_once

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


async def main():
    await init_db()
    await run_pipeline_once()


if __name__ == "__main__":
    asyncio.run(main())
