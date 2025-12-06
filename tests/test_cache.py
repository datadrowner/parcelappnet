"""Test ParcelApp local cache logic."""
import os
import pytest
from custom_components.parcelapp.cache import ParcelAppCache

def test_cache_save_and_load(tmp_path):
    db_path = tmp_path / "test_cache.sqlite3"
    cache = ParcelAppCache(str(db_path))
    deliveries = [
        {"tracking_number": "1", "description": "A"},
        {"tracking_number": "2", "description": "B"},
    ]
    cache.save_deliveries(deliveries)
    loaded = cache.load_deliveries()
    assert len(loaded) == 2
    assert any(d["tracking_number"] == "1" for d in loaded)
    assert any(d["tracking_number"] == "2" for d in loaded)

    # Overwrite and test clear
    cache.clear()
    assert cache.load_deliveries() == []
