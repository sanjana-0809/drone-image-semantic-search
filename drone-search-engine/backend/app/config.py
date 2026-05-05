"""Runtime configuration for the drone search backend."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os


def _split_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip().rstrip("/") for item in value.split(",") if item.strip())


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    environment: str
    frontend_url: str
    cors_origins: tuple[str, ...]
    base_url: str
    backend_dir: Path
    images_dir: Path
    reports_dir: Path
    db_path: Path
    max_upload_size_bytes: int
    max_batch_files: int
    max_filename_length: int
    max_image_pixels: int
    allowed_image_extensions: frozenset[str]
    allowed_image_mime_types: frozenset[str]
    allowed_image_formats: frozenset[str]
    search_score_threshold: float
    qdrant_url: str | None
    qdrant_api_key: str | None
    qdrant_host: str
    qdrant_port: int
    cloudinary_folder: str


@lru_cache
def get_settings() -> Settings:
    backend_dir = Path(__file__).resolve().parents[1]
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    cors_origins = _split_csv(os.getenv("CORS_ORIGINS")) or (
        frontend_url,
        "http://127.0.0.1:3000",
    )

    return Settings(
        app_name="Drone Image Semantic Search Engine",
        app_version=os.getenv("APP_VERSION", "1.1.0"),
        environment=os.getenv("ENVIRONMENT", "development").lower(),
        frontend_url=frontend_url,
        cors_origins=cors_origins,
        base_url=os.getenv("BASE_URL", "http://localhost:8000").rstrip("/"),
        backend_dir=backend_dir,
        images_dir=backend_dir / "images",
        reports_dir=backend_dir / "reports",
        db_path=Path(os.getenv("SQLITE_DB_PATH", backend_dir / "drone_search.db")),
        max_upload_size_bytes=_int_env("MAX_UPLOAD_SIZE_MB", 25) * 1024 * 1024,
        max_batch_files=_int_env("MAX_BATCH_FILES", 25),
        max_filename_length=_int_env("MAX_FILENAME_LENGTH", 160),
        max_image_pixels=_int_env("MAX_IMAGE_PIXELS", 50_000_000),
        allowed_image_extensions=frozenset({".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}),
        allowed_image_mime_types=frozenset({
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/tiff",
            "image/x-tiff",
            "image/bmp",
            "image/x-ms-bmp",
        }),
        allowed_image_formats=frozenset({"JPEG", "PNG", "WEBP", "TIFF", "BMP"}),
        search_score_threshold=_float_env("SEARCH_SCORE_THRESHOLD", 0.18),
        qdrant_url=os.getenv("QDRANT_URL"),
        qdrant_api_key=os.getenv("QDRANT_API_KEY"),
        qdrant_host=os.getenv("QDRANT_HOST", "localhost"),
        qdrant_port=_int_env("QDRANT_PORT", 6333),
        cloudinary_folder=os.getenv("CLOUDINARY_FOLDER", "drone-search"),
    )
