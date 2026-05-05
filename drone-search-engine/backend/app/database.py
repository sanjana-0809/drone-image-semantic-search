"""SQLite persistence for image metadata and generated reports."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import json
import sqlite3

from .config import get_settings


settings = get_settings()
DB_PATH = settings.db_path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection tuned for local app concurrency."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, name: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if name not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def init_db() -> None:
    """Create or migrate the local database schema."""
    with get_connection() as conn:
        conn.execute(
            """
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
                cloudinary_url TEXT,
                content_type TEXT,
                processing_status TEXT DEFAULT 'queued',
                processing_error TEXT
            )
            """
        )

        _ensure_column(conn, "images", "cloudinary_url", "TEXT")
        _ensure_column(conn, "images", "content_type", "TEXT")
        _ensure_column(conn, "images", "processing_status", "TEXT DEFAULT 'queued'")
        _ensure_column(conn, "images", "processing_error", "TEXT")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT NOT NULL,
                image_count INTEGER,
                created_at TEXT NOT NULL,
                report_data TEXT
            )
            """
        )

        conn.execute("CREATE INDEX IF NOT EXISTS idx_images_upload_date ON images(upload_date DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_images_processed ON images(processed)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at DESC)")


def save_image_metadata(
    image_id: str,
    filename: str,
    file_path: str,
    file_size: int,
    content_type: str | None = None,
) -> None:
    """Save initial upload metadata."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO images (
                image_id, filename, file_path, file_size, upload_date,
                content_type, processing_status, processed
            )
            VALUES (?, ?, ?, ?, ?, ?, 'queued', 0)
            """,
            (image_id, filename, file_path, file_size, _utc_now(), content_type),
        )


def update_image_ai_data(
    image_id: str,
    ai_results: dict[str, Any],
    *,
    mark_processed: bool | None = None,
    processing_status: str | None = None,
    processing_error: str | None = None,
) -> None:
    """Patch image metadata without overwriting fields that were not provided."""
    updates: list[str] = []
    params: list[Any] = []

    scalar_fields = {
        "caption": "caption",
        "ocr_text": "ocr_text",
        "cloudinary_url": "cloudinary_url",
    }
    list_fields = {
        "detected_objects": "detected_objects",
        "dominant_colors": "dominant_colors",
    }

    for key, column in scalar_fields.items():
        if key in ai_results:
            updates.append(f"{column} = ?")
            params.append(ai_results.get(key))

    for key, column in list_fields.items():
        if key in ai_results:
            updates.append(f"{column} = ?")
            params.append(json.dumps(ai_results.get(key) or []))

    if mark_processed is not None:
        updates.append("processed = ?")
        params.append(1 if mark_processed else 0)

    if processing_status is not None:
        updates.append("processing_status = ?")
        params.append(processing_status)

    if processing_error is not None:
        updates.append("processing_error = ?")
        params.append(processing_error[:1000] if processing_error else None)
    elif processing_status == "processed":
        updates.append("processing_error = NULL")

    if not updates:
        return

    params.append(image_id)
    with get_connection() as conn:
        conn.execute(
            f"UPDATE images SET {', '.join(updates)} WHERE image_id = ?",
            tuple(params),
        )


def update_image_processing_state(image_id: str, status: str, error: str | None = None) -> None:
    """Update just the background processing state for an image."""
    update_image_ai_data(
        image_id,
        {},
        mark_processed=(status == "processed"),
        processing_status=status,
        processing_error=error,
    )


def get_all_images() -> List[Dict[str, Any]]:
    """Get all images newest first."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM images ORDER BY upload_date DESC").fetchall()
    return [_row_to_dict(r) for r in rows]


def get_image_by_id(image_id: str) -> Optional[Dict[str, Any]]:
    """Get a single image by ID."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM images WHERE image_id = ?", (image_id,)).fetchone()
    return _row_to_dict(row) if row else None


def get_all_processed_images() -> List[Dict[str, Any]]:
    """Get images whose AI pipeline completed."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM images WHERE processed = 1 ORDER BY upload_date DESC"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def save_report(report: dict[str, Any]) -> None:
    """Save a generated report."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO reports (title, content, image_count, created_at, report_data)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                report.get("title", "Site Intelligence Report"),
                report.get("content", ""),
                report.get("image_count", 0),
                _utc_now(),
                json.dumps(report),
            ),
        )


def get_latest_report() -> Optional[Dict[str, Any]]:
    """Get the most recent report."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM reports ORDER BY created_at DESC LIMIT 1"
        ).fetchone()

    if not row:
        return None

    result = dict(row)
    if result.get("report_data"):
        try:
            result["report_data"] = json.loads(result["report_data"])
        except json.JSONDecodeError:
            pass
    return result


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert a row to a dictionary with parsed JSON fields."""
    d = dict(row)

    for field in ("detected_objects", "dominant_colors"):
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                d[field] = []
        else:
            d[field] = []

    d["processed"] = bool(d.get("processed", 0))
    return d
