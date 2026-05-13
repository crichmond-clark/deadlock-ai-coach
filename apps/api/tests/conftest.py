"""Pytest configuration and fixtures."""

import pytest

# Mark all async tests so pytest-asyncio runs them properly
pytest_plugins = ["pytest_asyncio"]


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
