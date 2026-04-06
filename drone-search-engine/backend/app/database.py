"""
Database layer — uses SQLite for zero-config local dev.
Switch to PostgreSQL for production by changing the connection.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "drone_search.db")


def get_connection():
    """Get SQLite connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS images (
            image_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            upload_date TEXT NOT NULL,
            caption TEXT,
            detected_objects TEXT,
            dominant_colors TEXT,
            ocr_text TEXT,
            processed INTEGER DEFAULT 0,
            cloudinary_url TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT NOT NULL,
            image_count INTEGER,
            created_at TEXT NOT NULL,
            report_data TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")


def update_image_ai_data(image_id: str, ai_results: dict):
    """Update image with AI pipeline results."""
    conn = get_connection()
    conn.execute(
        """UPDATE images SET
            caption = COALESCE(?, caption),
            detected_objects = COALESCE(?, detected_objects),
            dominant_colors = COALESCE(?, dominant_colors),
            ocr_text = COALESCE(?, ocr_text),
            cloudinary_url = COALESCE(?, cloudinary_url),
            processed = 1
           WHERE image_id = ?""",
        (
            ai_results.get("caption"),
            json.dumps(ai_results.get("detected_objects", [])) if ai_results.get("detected_objects") else None,
            json.dumps(ai_results.get("dominant_colors", [])) if ai_results.get("dominant_colors") else None,
            ai_results.get("ocr_text"),
            ai_results.get("cloudinary_url"),
            image_id
        )
    )
    conn.commit()
    conn.close()

def save_image_metadata(image_id: str, filename: str, file_path: str, file_size: int):
    """Save initial image metadata."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO images (image_id, filename, file_path, file_size, upload_date)
           VALUES (?, ?, ?, ?, ?)""",
        (image_id, filename, file_path, file_size, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
def update_image_ai_data(image_id: str, ai_results: dict):
    """Update image with AI pipeline results."""
    conn = get_connection()
    conn.execute(
        """UPDATE images SET
            caption = ?,
            detected_objects = ?,
            dominant_colors = ?,
            ocr_text = ?,
            processed = 1
           WHERE image_id = ?""",
        (
            ai_results.get("caption", ""),
            json.dumps(ai_results.get("detected_objects", [])),
            json.dumps(ai_results.get("dominant_colors", [])),
            ai_results.get("ocr_text", ""),
            image_id
        )
    )
    conn.commit()
    conn.close()


def get_all_images() -> List[Dict]:
    """Get all images."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM images ORDER BY upload_date DESC").fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_image_by_id(image_id: str) -> Optional[Dict]:
    """Get a single image by ID."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM images WHERE image_id = ?", (image_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def get_all_processed_images() -> List[Dict]:
    """Get all fully processed images."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM images WHERE processed = 1 ORDER BY upload_date DESC"
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def save_report(report: dict):
    """Save a generated report."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO reports (title, content, image_count, created_at, report_data)
           VALUES (?, ?, ?, ?, ?)""",
        (
            report.get("title", "Site Intelligence Report"),
            report.get("content", ""),
            report.get("image_count", 0),
            datetime.now().isoformat(),
            json.dumps(report)
        )
    )
    conn.commit()
    conn.close()


def get_latest_report() -> Optional[Dict]:
    """Get the most recent report."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM reports ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    
    if not row:
        return None
    
    result = dict(row)
    if result.get("report_data"):
        try:
            result["report_data"] = json.loads(result["report_data"])
        except json.JSONDecodeError:
            pass
    return result


def _row_to_dict(row) -> Dict:
    """Convert a database row to a dictionary with parsed JSON fields."""
    if not row:
        return {}
    
    d = dict(row)
    
    # Parse JSON fields
    for field in ["detected_objects", "dominant_colors"]:
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                d[field] = []
    
    d["processed"] = bool(d.get("processed", 0))
    return d
