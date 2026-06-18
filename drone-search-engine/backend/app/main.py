"""FastAPI backend for drone image semantic search."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import gc
import json
import logging
import os
import re
import threading
import uuid

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError

from .ai_pipeline import generate_clip_embedding, process_image, text_to_embedding
from .cloudinary_helper import upload_to_cloudinary
from .config import get_settings
from .database import (
    get_connection,
    clear_all_data,
    count_images,
    get_all_images,
    get_all_processed_images,
    get_image_by_id,
    get_latest_report,
    init_db,
    save_image_metadata,
    save_report,
    update_image_ai_data,
    update_image_processing_state,
)
from .report_generator import export_report_pdf, generate_site_report
from .vector_store import (
    VectorStoreUnavailable,
    count_points,
    get_vector_store_status,
    init_qdrant,
    reset_collection,
    search_similar,
    upsert_embedding,
)


settings = get_settings()
Image.MAX_IMAGE_PIXELS = settings.max_image_pixels
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 1024
FORMAT_EXTENSIONS = {
    "JPEG": {".jpg", ".jpeg"},
    "PNG": {".png"},
    "WEBP": {".webp"},
    "TIFF": {".tif", ".tiff"},
    "BMP": {".bmp"},
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.images_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    if init_qdrant():
        logger.info("Qdrant vector store ready")
        _reconcile_vector_store()
    else:
        logger.warning("Qdrant vector store unavailable; uploads will work but semantic search is degraded")
    logger.info("%s ready", settings.app_name)
    yield


def _reconcile_vector_store() -> None:
    """Keep the vector store consistent with the database on ephemeral hosting.

    When the app runs without persistent storage, the SQLite database is wiped on
    each restart while the external Qdrant collection survives. That leaves vectors
    with no metadata to resolve to, which makes search return empty results. If the
    database is empty but the collection still holds points, those points are
    orphaned, so clear them to start from a consistent, empty state. This never runs
    when the database has data (e.g. when persistent storage is configured).
    """
    try:
        if count_images() == 0:
            orphaned = count_points() or 0
            if orphaned > 0:
                removed = reset_collection()
                logger.warning(
                    "Database is empty but vector store held %d point(s); cleared orphaned vectors",
                    removed,
                )
    except Exception:
        logger.exception("Vector store reconcile skipped")


app = FastAPI(
    title=settings.app_name,
    description="AI-powered search through aerial drone imagery using natural language",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)

# Paths reachable without the access key: health/landing probes, API docs, and
# image files (loaded by <img> tags that cannot send an Authorization header).
_OPEN_PATHS = {"/", "/health", "/docs", "/redoc", "/openapi.json"}
_OPEN_PREFIXES = ("/images",)


@app.middleware("http")
async def access_guard(request, call_next):
    """Require a shared access key on protected routes when APP_ACCESS_KEY is set.

    Auth is disabled (open) when APP_ACCESS_KEY is unset, so the app still runs
    without configuration. The frontend proxy attaches this key server-side, so
    it is never exposed to the browser.
    """
    key = settings.app_access_key
    path = request.url.path
    is_open = path in _OPEN_PATHS or path.startswith(_OPEN_PREFIXES)
    if key and request.method != "OPTIONS" and not is_open:
        if request.headers.get("authorization") != f"Bearer {key}":
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)

app.mount("/images", StaticFiles(directory=settings.images_dir), name="images")


@app.get("/")
async def root():
    """Simple landing response for hosted health probes and the Hugging Face App tab."""
    return {
        "name": settings.app_name,
        "status": "online",
        "health": "/health",
        "docs": "/docs",
    }


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(default=10, ge=1, le=50)


class SearchResult(BaseModel):
    image_id: str
    filename: str
    image_url: str
    similarity_score: float
    above_threshold: bool = True
    caption: Optional[str] = None
    detected_objects: Optional[List[str]] = None
    dominant_colors: Optional[List[str]] = None
    ocr_text: Optional[str] = None


class ImageInfo(BaseModel):
    image_id: str
    filename: str
    image_url: str
    upload_date: str
    file_size: Optional[int] = None
    caption: Optional[str] = None
    detected_objects: Optional[List[str]] = None
    dominant_colors: Optional[List[str]] = None
    ocr_text: Optional[str] = None
    processed: bool = False
    processing_status: str = "queued"
    processing_error: Optional[str] = None


def _safe_original_filename(filename: str | None) -> str:
    raw = (filename or "upload").replace("\\", "/").split("/")[-1]
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", raw).strip(" .")
    if not cleaned:
        cleaned = "upload"
    return cleaned[: settings.max_filename_length]


def _public_image_url(image: dict) -> str:
    cloudinary_url = image.get("cloudinary_url")
    if cloudinary_url:
        return cloudinary_url
    return f"{settings.base_url}/images/{Path(image['file_path']).name}"


def _validate_image_id(image_id: str) -> str:
    try:
        return str(uuid.UUID(image_id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid image id") from exc


def _validate_image_file(file_path: Path, ext: str) -> None:
    try:
        with Image.open(file_path) as image:
            image.verify()

        with Image.open(file_path) as image:
            image_format = image.format
            width, height = image.size

        if image_format not in settings.allowed_image_formats:
            raise HTTPException(status_code=415, detail=f"Unsupported image format: {image_format or 'unknown'}")

        if ext not in FORMAT_EXTENSIONS.get(image_format, set()):
            raise HTTPException(status_code=400, detail="File extension does not match image content")

        if width <= 0 or height <= 0 or width * height > settings.max_image_pixels:
            raise HTTPException(status_code=413, detail="Image dimensions are too large")
    except DecompressionBombError as exc:
        raise HTTPException(status_code=413, detail="Image dimensions are too large") from exc
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image") from exc
    except OSError as exc:
        raise HTTPException(status_code=400, detail="Uploaded image could not be read") from exc


async def _store_upload(file: UploadFile) -> dict:
    original_filename = _safe_original_filename(file.filename)
    ext = Path(original_filename).suffix.lower()
    if ext not in settings.allowed_image_extensions:
        allowed = ", ".join(sorted(settings.allowed_image_extensions))
        raise HTTPException(status_code=415, detail=f"Unsupported file type. Allowed: {allowed}")

    content_type = (file.content_type or "").lower()
    if content_type and content_type not in settings.allowed_image_mime_types:
        raise HTTPException(status_code=415, detail=f"Unsupported content type: {content_type}")

    image_id = str(uuid.uuid4())
    safe_filename = f"{image_id}{ext}"
    file_path = settings.images_dir / safe_filename
    total = 0

    try:
        with file_path.open("xb") as output:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > settings.max_upload_size_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Image exceeds {settings.max_upload_size_bytes // (1024 * 1024)} MB limit",
                    )
                output.write(chunk)

        if total == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        _validate_image_file(file_path, ext)
        save_image_metadata(
            image_id=image_id,
            filename=original_filename,
            file_path=safe_filename,
            file_size=total,
            content_type=content_type or None,
        )

        return {
            "image_id": image_id,
            "filename": original_filename,
            "file_path": file_path,
            "file_size": total,
        }
    except HTTPException:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


# Cap how many images run the heavy AI pipeline at once. The CV/embedding models
# are memory-hungry, and several concurrent inferences will OOM a small instance
# (e.g. the 16 GB free tier). Default to 1 so uploads queue and process serially.
_processing_slots = threading.Semaphore(max(1, int(os.getenv("MAX_CONCURRENT_PROCESSING", "1"))))


def _process_image_job(image_id: str, file_path: str, filename: str) -> None:
    """Serialized wrapper around the AI pipeline to bound peak memory usage."""
    acquired = _processing_slots.acquire(timeout=float(os.getenv("PROCESSING_QUEUE_TIMEOUT", "600")))
    if not acquired:
        logger.error("Processing slot wait timed out for %s", filename)
        update_image_processing_state(image_id, "failed", "Server was busy; processing timed out. Try again.")
        return
    try:
        _run_image_pipeline(image_id, file_path, filename)
    finally:
        _processing_slots.release()
        # Release intermediate tensors/buffers between images so memory does not creep.
        gc.collect()


def _run_image_pipeline(image_id: str, file_path: str, filename: str) -> None:
    """Run AI processing, vector indexing, and optional cloud upload off the request path.

    Status reflects what actually succeeded:
      - ``failed``    embedding/indexing failed -> the image is not searchable.
      - ``partial``   searchable, but one or more metadata stages failed.
      - ``processed`` searchable with full metadata.
    """
    update_image_processing_state(image_id, "processing")

    ai_results: dict = {}
    stage_errors: dict[str, str] = {}
    try:
        ai_results, stage_errors = process_image(file_path)
    except Exception as exc:  # unexpected: the pipeline itself is resilient per-stage
        logger.exception("AI pipeline crashed for %s", filename)
        stage_errors = {"pipeline": str(exc) or exc.__class__.__name__}

    # Persist whatever metadata we extracted, even if some stages failed.
    if ai_results:
        update_image_ai_data(image_id, ai_results)

    # Embedding + indexing decides whether the image is searchable at all.
    indexed = False
    try:
        embedding = generate_clip_embedding(file_path)
        upsert_embedding(
            image_id,
            embedding,
            {
                "filename": filename,
                "caption": ai_results.get("caption", ""),
                "objects": ai_results.get("detected_objects", []),
            },
        )
        indexed = True
    except Exception:
        logger.exception("Embedding/indexing failed for %s", filename)

    if not indexed:
        update_image_processing_state(
            image_id, "failed", "Embedding/indexing failed; image is not searchable."
        )
    elif stage_errors:
        failed = ", ".join(sorted(stage_errors))
        update_image_ai_data(
            image_id,
            {},
            mark_processed=True,
            processing_status="partial",
            processing_error=f"Searchable, but these stages failed: {failed}.",
        )
    else:
        update_image_ai_data(
            image_id,
            {},
            mark_processed=True,
            processing_status="processed",
            processing_error=None,
        )

    try:
        cloudinary_url = upload_to_cloudinary(file_path, image_id)
        update_image_ai_data(image_id, {"cloudinary_url": cloudinary_url})
    except Exception as exc:
        logger.info("Cloudinary upload skipped or failed for %s: %s", filename, exc)


def _to_image_info(img: dict) -> ImageInfo:
    return ImageInfo(
        image_id=img["image_id"],
        filename=img["filename"],
        image_url=_public_image_url(img),
        upload_date=img["upload_date"],
        file_size=img.get("file_size"),
        caption=img.get("caption"),
        detected_objects=img.get("detected_objects"),
        dominant_colors=img.get("dominant_colors"),
        ocr_text=img.get("ocr_text"),
        processed=img.get("processed", False),
        processing_status=img.get("processing_status") or "queued",
        processing_error=img.get("processing_error"),
    )


@app.post("/upload", response_model=dict, status_code=202)
async def upload_image(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload one drone image and queue AI processing."""
    record = await _store_upload(file)
    background_tasks.add_task(
        _process_image_job,
        record["image_id"],
        str(record["file_path"]),
        record["filename"],
    )

    return {
        "status": "queued",
        "image_id": record["image_id"],
        "filename": record["filename"],
        "file_size": record["file_size"],
        "ai_results": {},
    }


@app.post("/upload-batch", response_model=dict, status_code=202)
async def upload_batch(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    """Upload multiple drone images and queue AI processing for each valid file."""
    if len(files) > settings.max_batch_files:
        raise HTTPException(status_code=413, detail=f"Batch limit is {settings.max_batch_files} files")

    results = []
    errors = []

    for file in files:
        filename = _safe_original_filename(file.filename)
        try:
            record = await _store_upload(file)
            background_tasks.add_task(
                _process_image_job,
                record["image_id"],
                str(record["file_path"]),
                record["filename"],
            )
            results.append(
                {
                    "image_id": record["image_id"],
                    "filename": record["filename"],
                    "file_size": record["file_size"],
                    "status": "queued",
                }
            )
        except HTTPException as exc:
            errors.append({"filename": filename, "error": exc.detail})
        except Exception as exc:
            logger.exception("Unexpected upload failure for %s", filename)
            errors.append({"filename": filename, "error": str(exc)})

    return {
        "queued": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors,
    }


@app.post("/search", response_model=List[SearchResult])
async def search_images(request: SearchRequest):
    """Search drone images using a natural-language query."""
    query = " ".join(request.query.split())
    if not query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    try:
        vector_status = get_vector_store_status(check=True)
        if not vector_status["available"]:
            raise VectorStoreUnavailable(vector_status.get("error") or "Qdrant vector store is unavailable.")

        query_embedding = text_to_embedding(query)
        qdrant_results = search_similar(query_embedding, top_k=request.top_k)
    except VectorStoreUnavailable as exc:
        logger.warning("Search unavailable: %s", exc)
        raise HTTPException(status_code=503, detail=f"Vector search is unavailable: {exc}") from exc
    except Exception as exc:
        logger.exception("Search failed")
        raise HTTPException(status_code=503, detail="Search service is unavailable") from exc

    # CLIP similarity scores for relevant aerial imagery often sit just under the
    # threshold, so a strict filter can return nothing even when a clearly relevant
    # image exists. Prefer confident matches, but fall back to the closest few
    # (flagged as below-threshold) instead of an empty, confusing result set.
    threshold = settings.search_score_threshold
    strong_hits = [hit for hit in qdrant_results if hit["score"] >= threshold]
    selected_hits = strong_hits or qdrant_results[: settings.search_fallback_results]

    results = []
    for hit in selected_hits:
        image = get_image_by_id(hit["image_id"])
        if image:
            results.append(
                SearchResult(
                    image_id=hit["image_id"],
                    filename=image["filename"],
                    image_url=_public_image_url(image),
                    similarity_score=round(hit["score"], 4),
                    above_threshold=hit["score"] >= threshold,
                    caption=image.get("caption"),
                    detected_objects=image.get("detected_objects"),
                    dominant_colors=image.get("dominant_colors"),
                    ocr_text=image.get("ocr_text"),
                )
            )

    return results


@app.post("/clear")
async def clear_all(confirm: bool = False):
    """Delete all images, vectors, reports, and stored files. Requires confirm=true.

    This is a destructive maintenance action with no authentication; in a
    multi-user/production deployment it must be protected behind auth.
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="Pass confirm=true to clear all data.")

    deleted = clear_all_data()

    removed_files = 0
    for path in settings.images_dir.glob("*"):
        if path.is_file() and path.name != ".gitkeep":
            try:
                path.unlink()
                removed_files += 1
            except OSError:
                logger.warning("Could not delete image file %s", path.name)

    vectors_removed = 0
    try:
        vectors_removed = reset_collection()
    except Exception:
        logger.exception("Vector store reset during clear failed")

    logger.info(
        "Cleared collection: %d images, %d files, %d vectors, %d reports",
        deleted["images"], removed_files, vectors_removed, deleted["reports"],
    )
    return {
        "status": "cleared",
        "images_deleted": deleted["images"],
        "files_deleted": removed_files,
        "vectors_deleted": vectors_removed,
        "reports_deleted": deleted["reports"],
    }


@app.get("/images-list", response_model=List[ImageInfo])
async def list_images():
    """List all uploaded images with metadata."""
    return [_to_image_info(img) for img in get_all_images()]


@app.get("/image/{image_id}")
async def get_image_detail(image_id: str):
    """Get full detail for a single image."""
    image = get_image_by_id(_validate_image_id(image_id))
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    image["image_url"] = _public_image_url(image)
    return image


@app.get("/stats")
async def get_stats():
    """Get collection statistics."""
    images = get_all_images()
    processed = [img for img in images if img.get("processed")]

    all_objects = []
    for img in processed:
        all_objects.extend(img.get("detected_objects") or [])

    from collections import Counter

    return {
        "total_images": len(images),
        "processed_images": len(processed),
        "queued_images": len([img for img in images if img.get("processing_status") == "queued"]),
        "failed_images": len([img for img in images if img.get("processing_status") == "failed"]),
        "top_objects": dict(Counter(all_objects).most_common(20)),
        "last_updated": images[0]["upload_date"] if images else None,
    }


@app.post("/generate-report")
async def generate_report():
    """Generate a site intelligence report from processed images."""
    images = get_all_processed_images()
    if not images:
        raise HTTPException(status_code=400, detail="No processed images found. Upload and process images first.")

    try:
        report = generate_site_report(images)
        save_report(report)
        return {"status": "success", "report": report}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Report generation failed")
        raise HTTPException(status_code=502, detail="Report generation failed") from exc


@app.get("/report")
async def get_report():
    """Get the latest generated report."""
    report = get_latest_report()
    if not report:
        raise HTTPException(status_code=404, detail="No report generated yet. Use POST /generate-report first.")
    return report


@app.post("/export-report")
async def export_report():
    """Export the latest report as a PDF file."""
    report = get_latest_report()
    if not report:
        raise HTTPException(status_code=404, detail="No report to export. Generate one first.")

    pdf_path = Path(export_report_pdf(report, str(settings.reports_dir))).resolve()
    reports_root = settings.reports_dir.resolve()
    if reports_root not in pdf_path.parents:
        raise HTTPException(status_code=500, detail="Report export path is invalid")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="site_intelligence_report.pdf",
    )


def _database_health() -> dict:
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        return {"available": True, "error": None}
    except Exception as exc:
        logger.exception("Database health check failed")
        return {"available": False, "error": str(exc) or exc.__class__.__name__}


@app.get("/health")
async def health():
    database_status = _database_health()
    vector_status = get_vector_store_status(check=True)

    status = "healthy"
    if not database_status["available"]:
        status = "unhealthy"
    elif not vector_status["available"]:
        status = "degraded"

    return {
        "status": status,
        "version": settings.app_version,
        "environment": settings.environment,
        "services": {
            "database": database_status,
            "vector_store": vector_status,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
