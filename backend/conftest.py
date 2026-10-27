"""Root pytest fixtures."""
import pytest


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    """DRF throttles share the locmem cache across tests — reset before each test."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()
