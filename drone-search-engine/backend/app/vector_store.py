"""Qdrant vector store operations for semantic image search."""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any
from urllib.parse import urlparse, urlunparse

from .config import get_settings


COLLECTION_NAME = "drone_images"
VECTOR_DIM = 768

settings = get_settings()
_client: Any | None = None
_collection_ready = False
_last_error: str | None = None
logger = logging.getLogger(__name__)


class VectorStoreUnavailable(RuntimeError):
    """Raised when vector search cannot be used safely."""


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _qdrant_url() -> str | None:
    if not settings.qdrant_url:
        return None

    parsed = urlparse(settings.qdrant_url)
    if not parsed.scheme:
        parsed = urlparse(f"https://{settings.qdrant_url}")

    hostname = parsed.hostname or ""
    if hostname.endswith(".cloud.qdrant.io") and parsed.port in {6333, 6334}:
        netloc = hostname
        if parsed.username:
            netloc = f"{parsed.username}@{netloc}"
        parsed = parsed._replace(netloc=netloc)

    return urlunparse(parsed).rstrip("/")


def _backend_label() -> str:
    qdrant_url = _qdrant_url()
    if qdrant_url:
        return qdrant_url
    return f"{settings.qdrant_host}:{settings.qdrant_port}"


def _error_message(exc: Exception) -> str:
    if isinstance(exc, ModuleNotFoundError) and exc.name == "qdrant_client":
        return "qdrant-client is not installed. Run `pip install -r requirements.txt` in the backend environment."
    return str(exc) or exc.__class__.__name__


def _mark_unavailable(exc: Exception, context: str) -> str:
    global _collection_ready, _last_error

    message = _error_message(exc)
    _collection_ready = False
    _last_error = message
    logger.warning("%s unavailable at %s: %s", context, _backend_label(), message)
    return message


def _get_client() -> Any:
    global _client
    if _client is None:
        from qdrant_client import QdrantClient

        qdrant_url = _qdrant_url()
        if qdrant_url:
            _client = QdrantClient(
                url=qdrant_url,
                api_key=settings.qdrant_api_key,
                timeout=_float_env("QDRANT_TIMEOUT_SECONDS", 3.0),
            )
        else:
            _client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                timeout=_float_env("QDRANT_TIMEOUT_SECONDS", 3.0),
            )
    return _client


def _validate_vector(vector: list[float]) -> None:
    if len(vector) != VECTOR_DIM:
        raise ValueError(f"Expected a {VECTOR_DIM}-dimension embedding, got {len(vector)}")


def init_qdrant() -> bool:
    """Create the collection if it does not exist.

    Returns False instead of crashing app startup when Qdrant is missing. Uploads
    and metadata endpoints can still run; search will report a clear 503.
    """
    global _collection_ready, _last_error

    try:
        from qdrant_client.models import Distance, VectorParams
    except Exception as exc:
        _mark_unavailable(exc, "Qdrant client")
        return False

    try:
        client = _get_client()
        collection_names = {c.name for c in client.get_collections().collections}

        if COLLECTION_NAME not in collection_names:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            )

        _collection_ready = True
        _last_error = None
        return True
    except Exception as exc:
        _mark_unavailable(exc, "Qdrant")
        return False


def _ensure_ready() -> None:
    if _collection_ready or init_qdrant():
        return
    raise VectorStoreUnavailable(_last_error or "Qdrant vector store is unavailable.")


def upsert_embedding(image_id: str, embedding: list[float], payload: dict[str, Any] | None = None) -> None:
    """Store an image embedding in Qdrant."""
    _validate_vector(embedding)
    _ensure_ready()

    from qdrant_client.models import PointStruct

    client = _get_client()

    point = PointStruct(
        id=str(uuid.uuid5(uuid.NAMESPACE_DNS, image_id)),
        vector=embedding,
        payload={
            "image_id": image_id,
            **(payload or {}),
        },
    )

    client.upsert(collection_name=COLLECTION_NAME, points=[point])


def search_similar(query_embedding: list[float], top_k: int = 10) -> list[dict[str, Any]]:
    """Search for visually similar images by vector similarity."""
    _validate_vector(query_embedding)
    _ensure_ready()
    client = _get_client()

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding,
        limit=top_k,
    )

    return [
        {
            "image_id": hit.payload.get("image_id", "") if hit.payload else "",
            "score": float(hit.score),
            "payload": hit.payload or {},
        }
        for hit in results
    ]


def get_collection_info() -> dict[str, int | None]:
    """Get collection stats."""
    _ensure_ready()
    info = _get_client().get_collection(COLLECTION_NAME)
    return {
        "vectors_count": info.vectors_count,
        "points_count": info.points_count,
    }


def get_vector_store_status(*, check: bool = True) -> dict[str, Any]:
    """Return safe health details for the vector search dependency."""
    if check:
        init_qdrant()

    return {
        "available": _collection_ready,
        "collection": COLLECTION_NAME,
        "backend": _backend_label(),
        "error": _last_error,
    }
