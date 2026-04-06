"""
Qdrant Vector Store — handles all vector database operations.
Stores CLIP embeddings for semantic image search.

Requires: docker run -p 6333:6333 qdrant/qdrant
"""
import os
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct, Filter
)
import uuid

COLLECTION_NAME = "drone_images"
VECTOR_DIM = 768  # CLIP ViT-L/14 output dimension

_client = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        if qdrant_url:
            # Production: Qdrant Cloud
            _client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        else:
            # Local dev fallback
            _client = QdrantClient(host="localhost", port=6333)
    return _client


def init_qdrant():
    """Create the collection if it doesn't exist."""
    client = _get_client()
    
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    
    if COLLECTION_NAME not in collection_names:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_DIM,
                distance=Distance.COSINE,
            ),
        )
        print(f"✅ Created Qdrant collection: {COLLECTION_NAME}")
    else:
        print(f"✅ Qdrant collection '{COLLECTION_NAME}' already exists")


def upsert_embedding(image_id: str, embedding: list, payload: dict = None):
    """Store an image embedding in Qdrant."""
    client = _get_client()
    
    point = PointStruct(
        id=str(uuid.uuid5(uuid.NAMESPACE_DNS, image_id)),
        vector=embedding,
        payload={
            "image_id": image_id,
            **(payload or {})
        }
    )
    
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[point]
    )


def search_similar(query_embedding: list, top_k: int = 10) -> list:
    """Search for similar images by vector similarity."""
    client = _get_client()
    
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding,
        limit=top_k,
    )
    
    return [
        {
            "image_id": hit.payload.get("image_id", ""),
            "score": hit.score,
            "payload": hit.payload,
        }
        for hit in results
    ]


def get_collection_info() -> dict:
    """Get collection stats."""
    client = _get_client()
    info = client.get_collection(COLLECTION_NAME)
    return {
        "vectors_count": info.vectors_count,
        "points_count": info.points_count,
    }

