import os
import sqlite3
import json
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional

class IncidentDatabase:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "incidents.db")
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_path TEXT NOT NULL,
                    heatmap_path TEXT,
                    embedding TEXT NOT NULL,
                    confirmed_diagnosis TEXT NOT NULL,
                    fix_steps TEXT NOT NULL,
                    voice_note_path TEXT,
                    confidence_at_capture REAL,
                    timestamp TEXT NOT NULL,
                    seeded INTEGER DEFAULT 0,
                    provenance TEXT DEFAULT 'seeded_dataset',
                    sensor_data TEXT DEFAULT '{}',
                    confirmed INTEGER DEFAULT 1
                )
            """)
            # Auto-migrate columns if table already existed without them
            cursor.execute("PRAGMA table_info(incidents)")
            cols = [info[1] for info in cursor.fetchall()]
            if "provenance" not in cols:
                cursor.execute("ALTER TABLE incidents ADD COLUMN provenance TEXT DEFAULT 'seeded_dataset'")
            if "sensor_data" not in cols:
                cursor.execute("ALTER TABLE incidents ADD COLUMN sensor_data TEXT DEFAULT '{}'")
            if "confirmed" not in cols:
                cursor.execute("ALTER TABLE incidents ADD COLUMN confirmed INTEGER DEFAULT 1")
            conn.commit()

    def insert_incident(
        self,
        image_path: str,
        embedding: np.ndarray,
        confirmed_diagnosis: str,
        fix_steps: str,
        heatmap_path: Optional[str] = None,
        voice_note_path: Optional[str] = None,
        confidence_at_capture: float = 0.85,
        seeded: bool = False,
        provenance: str = "seeded_dataset",
        sensor_data: Optional[Dict[str, Any]] = None,
        confirmed: bool = True
    ) -> int:
        """Inserts incident record into SQLite store"""
        embedding_json = json.dumps(embedding.tolist())
        timestamp_str = datetime.utcnow().isoformat()
        seeded_int = 1 if seeded else 0
        confirmed_int = 1 if confirmed else 0
        sensor_data_json = json.dumps(sensor_data or {})

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO incidents (
                    image_path, heatmap_path, embedding, confirmed_diagnosis,
                    fix_steps, voice_note_path, confidence_at_capture, timestamp, seeded,
                    provenance, sensor_data, confirmed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image_path, heatmap_path, embedding_json, confirmed_diagnosis,
                fix_steps, voice_note_path, confidence_at_capture, timestamp_str, seeded_int,
                provenance, sensor_data_json, confirmed_int
            ))
            conn.commit()
            return cursor.lastrowid

    def get_all_incidents(self) -> List[Dict[str, Any]]:
        """Fetches all stored incident records with parsed numpy embeddings"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, image_path, heatmap_path, embedding, confirmed_diagnosis,
                       fix_steps, voice_note_path, confidence_at_capture, timestamp, seeded,
                       provenance, sensor_data, confirmed
                FROM incidents
            """)
            rows = cursor.fetchall()
            
        results = []
        for r in rows:
            sensor_dict = {}
            if r[11]:
                try:
                    sensor_dict = json.loads(r[11])
                except Exception:
                    pass

            results.append({
                "id": r[0],
                "image_path": r[1],
                "heatmap_path": r[2],
                "embedding": np.array(json.loads(r[3]), dtype=np.float32),
                "confirmed_diagnosis": r[4],
                "fix_steps": r[5],
                "voice_note_path": r[6],
                "confidence_at_capture": r[7],
                "timestamp": r[8],
                "seeded": bool(r[9]),
                "provenance": r[10] or "seeded_dataset",
                "sensor_data": sensor_dict,
                "confirmed": bool(r[12])
            })
        return results

    def clear_database(self):
        """Clears all entries (useful for reset/re-seeding)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM incidents")
            conn.commit()
