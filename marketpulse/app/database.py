"""
app/database.py — Async SQLAlchemy engine + session factory.
Call init_db() once at startup to create all tables.
"""
import logging
import socket
import asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

# Async engine — pool_pre_ping keeps connections healthy
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=5,
    echo=False,  # set True to see SQL in logs
)

# Session factory — used everywhere as dependency
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """All ORM models inherit from this."""
    pass


def _start_postgres_service() -> None:
    """Blocking call to start the Windows PostgreSQL service via PowerShell (runs in thread pool)."""
    import subprocess
    subprocess.run([
        "powershell", "-Command",
        "Start-Process powershell -Verb runAs -ArgumentList '-Command Start-Service postgresql-x64-18'"
    ], check=True)


def _check_postgres_port() -> int:
    """Synchronous socket check to see if port 5432 is open."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex(('127.0.0.1', 5432))

async def check_and_start_postgres():
    """Checks if Postgres is running on port 5432. If not, requests Admin permission to start the Windows service."""
    result = await asyncio.to_thread(_check_postgres_port)

    if result == 0:
        logger.info("PostgreSQL is already running.")
        return

    logger.warning("PostgreSQL (port 5432) is NOT running. Attempting to start the service...")
    try:
        # Bug fix #12: subprocess.run is blocking — run it in a thread pool to avoid freezing the event loop
        await asyncio.to_thread(_start_postgres_service)

        logger.info("Waiting for PostgreSQL to start...")
        for _ in range(10):  # Wait up to 10 seconds
            await asyncio.sleep(1)
            if await asyncio.to_thread(_check_postgres_port) == 0:
                logger.info("PostgreSQL successfully started!")
                return
        logger.error("PostgreSQL did not start in time. You may need to start it manually.")
    except Exception as e:
        logger.error("Failed to automatically start PostgreSQL: %s", e)


async def ensure_database_exists() -> None:
    """Ensure the target PostgreSQL database exists before connecting."""
    try:
        from sqlalchemy.engine import make_url
        from sqlalchemy import text
        url = make_url(settings.database_url)
        target_db = url.database
        if not target_db:
            return

        # Connect to the default 'postgres' database to check/create target_db
        admin_url = url.set(database="postgres")
        admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")

        async with admin_engine.connect() as conn:
            check_query = text("SELECT 1 FROM pg_database WHERE datname = :dbname")
            result = await conn.scalar(check_query, {"dbname": target_db})
            if not result:
                logger.info("Database '%s' does not exist. Creating it...", target_db)
                await conn.execute(text(f'CREATE DATABASE "{target_db}"'))
                logger.info("Database '%s' created successfully.", target_db)

        await admin_engine.dispose()
    except Exception as e:
        logger.warning("Could not auto-create database: %s", e)


async def init_db() -> None:
    """Create all tables if they don't exist."""
    await check_and_start_postgres()
    await ensure_database_exists()
    from app import models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialised")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a session per request."""
    async with AsyncSessionLocal() as session:
        yield session
