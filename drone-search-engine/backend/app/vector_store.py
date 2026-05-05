"""Qdrant vector store operations for semantic image search."""

from __future__ import annotations

import uuid
from typing import Any

from .config import get_settings


COLLECTION_NAME = "drone_images"
VECTOR_DIM = 768

settings = get_settings()
_client: Any | None = None


def _get_client() -> Any:
    global _client
    if _client is None:
        from qdrant_client import QdrantClient

        if settings.qdrant_url:
            _client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        else:
            _client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _client


def _validate_vector(vector: list[float]) -> None:
    if len(vector) != VECTOR_DIM:
        raise ValueError(f"Expected a {VECTOR_DIM}-dimension embedding, got {len(vector)}")


def init_qdrant() -> None:
    """Create the collection if it does not exist."""
    from qdrant_client.models import Distance, VectorParams

    client = _get_client()
    collection_names = {c.name for c in client.get_collections().collections}

    if COLLECTION_NAME not in collection_names:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )


def upsert_embedding(image_id: str, embedding: list[float], payload: dict[str, Any] | None = None) -> None:
    """Store an image embedding in Qdrant."""
    from qdrant_client.models import PointStruct

    _validate_vector(embedding)
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
    info = _get_client().get_collection(COLLECTION_NAME)
    return {
        "vectors_count": info.vectors_count,
        "points_count": info.points_count,
    }
