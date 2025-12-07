import sqlite3
import json
import os
import logging
from typing import List, Dict, Any, Optional

_LOGGER = logging.getLogger(__name__)

CACHE_DB = os.path.join(os.path.dirname(__file__), "parcelapp_cache.sqlite3")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS deliveries (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

class ParcelAppCache:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or CACHE_DB
        self._ensure_db()

    def _ensure_db(self):
        """Ensure cache database exists and is initialized."""
        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                conn.execute(CREATE_TABLE_SQL)
                conn.commit()
        except sqlite3.Error as db_err:
            _LOGGER.error("Failed to initialize cache database: %s", db_err)
            raise

    def save_deliveries(self, deliveries: List[Dict[str, Any]]):
        """Save deliveries to cache database."""
        if not deliveries:
            return
        
        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                for delivery in deliveries:
                    tracking_number = delivery.get("tracking_number")
                    if not tracking_number:
                        _LOGGER.warning("Skipping delivery without tracking number")
                        continue
                    
                    try:
                        data_json = json.dumps(delivery)
                        conn.execute(
                            "REPLACE INTO deliveries (id, data) VALUES (?, ?)",
                            (tracking_number, data_json),
                        )
                    except (json.JSONEncodeError, TypeError) as json_err:
                        _LOGGER.error("Failed to serialize delivery %s: %s", tracking_number, json_err)
                        continue
                
                conn.commit()
        except sqlite3.Error as db_err:
            _LOGGER.error("Failed to save deliveries to cache: %s", db_err)

    def load_deliveries(self) -> List[Dict[str, Any]]:
        """Load deliveries from cache database."""
        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                cur = conn.execute("SELECT data FROM deliveries")
                deliveries = []
                for row in cur.fetchall():
                    try:
                        delivery = json.loads(row[0])
                        deliveries.append(delivery)
                    except json.JSONDecodeError as json_err:
                        _LOGGER.error("Failed to parse cached delivery: %s", json_err)
                        continue
                return deliveries
        except sqlite3.Error as db_err:
            _LOGGER.error("Failed to load deliveries from cache: %s", db_err)
            return []

    def clear(self):
        """Clear all cached deliveries."""
        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                conn.execute("DELETE FROM deliveries")
                conn.commit()
        except sqlite3.Error as db_err:
            _LOGGER.error("Failed to clear cache: %s", db_err)
