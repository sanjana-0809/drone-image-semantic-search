"""
Drone Image Semantic Search Engine — FastAPI Backend
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
import json
from datetime import datetime

from .database import (
    init_db, save_image_metadata, get_all_images,
    get_image_by_id, update_image_ai_data, save_report,
    get_latest_report, get_all_processed_images
)
from .ai_pipeline import process_image, generate_clip_embedding, text_to_embedding
from .vector_store import init_qdrant, upsert_embedding, search_similar
from .report_generator import generate_site_report, export_report_pdf

app = FastAPI(
    title="Drone Image Semantic Search Engine",
    description="AI-powered search through aerial drone imagery using natural language",
    version="1.0.0"
)

# CORS — allow Next.js frontend
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allows Vercel + local dev
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded images as static files
IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")
os.makedirs(IMAGES_DIR, exist_ok=True)
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


# ─── Pydantic Models ───────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10

class SearchResult(BaseModel):
    image_id: str
    filename: str
    image_url: str
    similarity_score: float
    caption: Optional[str] = None
    detected_objects: Optional[List[str]] = None
    dominant_colors: Optional[List[str]] = None
    ocr_text: Optional[str] = None

class ImageInfo(BaseModel):
    image_id: str
    filename: str
    image_url: str
    upload_date: str
    caption: Optional[str] = None
    detected_objects: Optional[List[str]] = None
    dominant_colors: Optional[List[str]] = None
    ocr_text: Optional[str] = None
    processed: bool = False


# ─── Startup ────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Initialize database and vector store on startup."""
    print("🚀 Initializing database...")
    init_db()
    print("🚀 Initializing Qdrant vector store...")
    init_qdrant()
    print("✅ Drone Search Engine ready!")


# ─── Upload Endpoints ──────────────────────────────────────────

@app.post("/upload", response_model=dict)
async def upload_image(file: UploadFile = File(...)):
    """Upload a single drone image, process it with AI, and index it."""
    
    # Validate file type
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"File type {ext} not supported. Use: {allowed}")
    
    # Save file
    image_id = str(uuid.uuid4())
    safe_filename = f"{image_id}{ext}"
    file_path = os.path.join(IMAGES_DIR, safe_filename)
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Save metadata to PostgreSQL
    save_image_metadata(
        image_id=image_id,
        filename=file.filename,
        file_path=safe_filename,
        file_size=len(content)
    )
    
    # Run AI pipeline
    try:
        ai_results = process_image(file_path)
        update_image_ai_data(image_id, ai_results)
    except Exception as e:
        print(f"⚠️ AI pipeline error for {file.filename}: {e}")
        ai_results = {}
    
    # Generate CLIP embedding and store in Qdrant
    try:
        embedding = generate_clip_embedding(file_path)
        upsert_embedding(image_id, embedding, {
            "filename": file.filename,
            "caption": ai_results.get("caption", ""),
            "objects": json.dumps(ai_results.get("detected_objects", [])),
        })
    except Exception as e:
        print(f"⚠️ Embedding error for {file.filename}: {e}")
    
    return {
        "status": "success",
        "image_id": image_id,
        "filename": file.filename,
        "ai_results": ai_results
    }


@app.post("/upload-batch", response_model=dict)
async def upload_batch(files: List[UploadFile] = File(...)):
    """Upload multiple drone images at once."""
    results = []
    errors = []
    
    for file in files:
        try:
            ext = os.path.splitext(file.filename)[1].lower()
            allowed = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"}
            if ext not in allowed:
                errors.append({"filename": file.filename, "error": f"Unsupported type: {ext}"})
                continue
            
            image_id = str(uuid.uuid4())
            safe_filename = f"{image_id}{ext}"
            file_path = os.path.join(IMAGES_DIR, safe_filename)
            
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            save_image_metadata(image_id, file.filename, safe_filename, len(content))
            
            # AI pipeline
            try:
                ai_results = process_image(file_path)
                update_image_ai_data(image_id, ai_results)
            except Exception as e:
                ai_results = {}
                print(f"⚠️ AI error for {file.filename}: {e}")
            
            # CLIP embedding
            try:
                embedding = generate_clip_embedding(file_path)
                upsert_embedding(image_id, embedding, {
                    "filename": file.filename,
                    "caption": ai_results.get("caption", ""),
                    "objects": json.dumps(ai_results.get("detected_objects", [])),
                })
            except Exception as e:
                print(f"⚠️ Embedding error: {e}")
            
            results.append({
                "image_id": image_id,
                "filename": file.filename,
                "status": "processed"
            })
        except Exception as e:
            errors.append({"filename": file.filename, "error": str(e)})
    
    return {
        "processed": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors
    }


# ─── Search Endpoint ───────────────────────────────────────────

@app.post("/search", response_model=List[SearchResult])
async def search_images(request: SearchRequest):
    """Search drone images using natural language query."""
    
    if not request.query.strip():
        raise HTTPException(400, "Search query cannot be empty")
    
    # Convert text query to CLIP embedding
    query_embedding = text_to_embedding(request.query)
    
    # Search Qdrant for similar images
    qdrant_results = search_similar(query_embedding, top_k=request.top_k)
        # Filter out low-similarity results
    qdrant_results = [hit for hit in qdrant_results if hit["score"] > 0.25]
    # Enrich with PostgreSQL metadata
    results = []
    for hit in qdrant_results:
        image_id = hit["image_id"]
        image = get_image_by_id(image_id)
        
        if image:
            results.append(SearchResult(
                image_id=image_id,
                filename=image["filename"],
                image_url=f"{os.getenv('BASE_URL', 'http://localhost:8000')}/images/{image['file_path']}",
                similarity_score=round(hit["score"], 4),
                caption=image.get("caption"),
                detected_objects=image.get("detected_objects"),
                dominant_colors=image.get("dominant_colors"),
                ocr_text=image.get("ocr_text"),
            ))
    
    return results


# ─── Images List ────────────────────────────────────────────────

@app.get("/images-list", response_model=List[ImageInfo])
async def list_images():
    """List all indexed images with metadata."""
    images = get_all_images()
    return [
        ImageInfo(
            image_id=img["image_id"],
            filename=img["filename"],
            image_url=f"/images/{img['file_path']}",
            upload_date=img["upload_date"],
            caption=img.get("caption"),
            detected_objects=img.get("detected_objects"),
            dominant_colors=img.get("dominant_colors"),
            ocr_text=img.get("ocr_text"),
            processed=img.get("processed", False),
        )
        for img in images
    ]


@app.get("/image/{image_id}")
async def get_image_detail(image_id: str):
    """Get full detail for a single image."""
    image = get_image_by_id(image_id)
    if not image:
        raise HTTPException(404, "Image not found")
    image["image_url"] = f"{os.getenv('BASE_URL', 'http://localhost:8000')}/images/{image['file_path']}"
    return image


# ─── Stats ──────────────────────────────────────────────────────

@app.get("/stats")
async def get_stats():
    """Get collection statistics."""
    images = get_all_images()
    processed = [img for img in images if img.get("processed")]
    
    all_objects = []
    for img in processed:
        objs = img.get("detected_objects", [])
        if objs:
            all_objects.extend(objs)
    
    from collections import Counter
    object_counts = dict(Counter(all_objects).most_common(20))
    
    return {
        "total_images": len(images),
        "processed_images": len(processed),
        "top_objects": object_counts,
        "last_updated": images[-1]["upload_date"] if images else None,
    }


# ─── Report Generation ─────────────────────────────────────────

@app.post("/generate-report")
async def generate_report():
    """Generate a Site Intelligence Report using Claude API."""
    images = get_all_processed_images()
    
    if not images or len(images) == 0:
        raise HTTPException(400, "No processed images found. Upload and process images first.")
    
    try:
        report = generate_site_report(images)
        save_report(report)
        return {"status": "success", "report": report}
    except Exception as e:
        raise HTTPException(500, f"Report generation failed: {str(e)}")


@app.get("/report")
async def get_report():
    """Get the latest generated report."""
    report = get_latest_report()
    if not report:
        raise HTTPException(404, "No report generated yet. Use POST /generate-report first.")
    return report


@app.post("/export-report")
async def export_report():
    """Export the latest report as a PDF file."""
    report = get_latest_report()
    if not report:
        raise HTTPException(404, "No report to export. Generate one first.")
    
    pdf_path = export_report_pdf(report, REPORTS_DIR)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="site_intelligence_report.pdf"
    )


# ─── Health Check ───────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
