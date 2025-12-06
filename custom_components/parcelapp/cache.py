import sqlite3
import json
import os
from typing import List, Dict, Any, Optional

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
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(CREATE_TABLE_SQL)

    def save_deliveries(self, deliveries: List[Dict[str, Any]]):
        with sqlite3.connect(self.db_path) as conn:
            for delivery in deliveries:
                conn.execute(
                    "REPLACE INTO deliveries (id, data) VALUES (?, ?)",
                    (delivery.get("tracking_number"), json.dumps(delivery)),
                )
            conn.commit()

    def load_deliveries(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT data FROM deliveries")
            return [json.loads(row[0]) for row in cur.fetchall()]

    def clear(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM deliveries")
            conn.commit()
