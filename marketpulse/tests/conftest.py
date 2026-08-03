"""
marketpulse/tests/conftest.py — Shared Pytest fixtures and backend configuration.
"""
import pytest


@pytest.fixture
def anyio_backend():
    """Specify anyio test backend as asyncio for async tests."""
    return 'asyncio'
