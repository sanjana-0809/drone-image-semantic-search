# Drone Image Semantic Search Engine

AI-powered search for aerial and drone imagery using natural-language queries, computer vision, vector search, and generated site reports.

## What It Does

1. Upload drone or aerial images.
2. The backend validates each image, stores it, and queues AI processing.
3. The AI pipeline extracts captions, objects, OCR text, dominant colors, and CLIP embeddings.
4. Qdrant stores vectors for semantic search.
5. Groq generates a site intelligence report that can be exported as PDF.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | FastAPI, SQLite |
| Frontend | Next.js 16, React 18, Tailwind CSS |
| Captioning | BLIP base |
| Object Detection | YOLOv8s |
| OCR | EasyOCR |
| Embeddings | OpenCLIP ViT-L/14 |
| Vector Search | Qdrant |
| Reports | Groq API + ReportLab |
| Optional Image Storage | Cloudinary |

## Security Hardening

- Restricted CORS with `CORS_ORIGINS` instead of wildcard origins.
- Same-origin frontend API calls through `/api` rewrites by default.
- Upload extension, MIME, size, image-content, and pixel-count validation.
- Background processing for single and batch uploads.
- Safer filename handling and UUID-only stored image paths.
- SQLite WAL mode, indexes, and schema migration for processing status fields.
- Lazy optional imports for Cloudinary and Qdrant.
- Prompt-injection guardrails for OCR/caption data used in report prompts.
- Escaped report text in PDF generation.
- Next.js security headers and disabled `X-Powered-By`.
- Frontend dependency audit cleaned with Next.js 16.2.4 and PostCSS 8.5.14 override.
- Docker backend runs as a non-root user.

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

Backend default: `http://127.0.0.1:8000`

Qdrant must be running locally unless `QDRANT_URL` is configured:

```bash
docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend default: `http://localhost:3000`

The frontend uses `/api` rewrites by default. Set `BACKEND_URL` for the server-side rewrite target, or set `NEXT_PUBLIC_API_URL` only when the browser must call the backend directly.

## Backend Environment

```env
ENVIRONMENT=development
HOST=127.0.0.1
PORT=8000
BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

MAX_UPLOAD_SIZE_MB=25
MAX_BATCH_FILES=25
MAX_IMAGE_PIXELS=50000000

QDRANT_HOST=localhost
QDRANT_PORT=6333
# QDRANT_URL=https://your-cluster.qdrant.io
# QDRANT_API_KEY=your_qdrant_api_key

GROQ_API_KEY=your_groq_api_key_here
GROQ_REPORT_MODEL=llama-3.3-70b-versatile

CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `POST` | `/upload` | Upload one image and queue processing |
| `POST` | `/upload-batch` | Upload multiple images and queue processing |
| `POST` | `/search` | Semantic image search |
| `GET` | `/images-list` | List uploaded images and processing status |
| `GET` | `/image/{id}` | Get one image |
| `GET` | `/stats` | Collection statistics |
| `POST` | `/generate-report` | Generate report from processed images |
| `GET` | `/report` | Get latest report |
| `POST` | `/export-report` | Download latest report as PDF |

## Verification

```bash
cd backend
python -m compileall app

cd ../frontend
npm audit --audit-level=moderate
npm run build
```
