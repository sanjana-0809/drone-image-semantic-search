# Drone Image Semantic Search Engine

AI-powered search through aerial drone imagery using natural language queries.

Exploring what's possible when you combine computer vision, vector search, and LLMs on real aerial data.

---

## What It Does

Upload drone/aerial images → AI processes each one (caption, object detection, OCR, color analysis) → Search the collection using plain English → Generate a Site Intelligence Report with Claude API → Export as PDF.

Example queries:
- `"construction site with cranes"`
- `"vehicles on road"`
- `"water body near buildings"`
- `"solar panels on rooftop"`
- `"highway intersection aerial view"`

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python) |
| Frontend | Next.js 14 (App Router) + Tailwind CSS |
| Image Captioning | BLIP base (Salesforce) |
| Object Detection | YOLOv8s (Ultralytics) |
| Text Extraction | EasyOCR |
| Color Analysis | OpenCV + K-means |
| Embeddings | CLIP ViT-L/14 (OpenCLIP) — 768-dim |
| Vector Search | Qdrant Cloud |
| Report Generation | Claude API (Anthropic) |
| Image Storage | Cloudinary (permanent cloud storage) |
| Database | SQLite |
| Backend Hosting | Hugging Face Spaces (Docker) |
| Frontend Hosting | Vercel |

---

## Live Demo

- **Frontend:** [drone-image-semantic-search.vercel.app](https://drone-image-semantic-search.vercel.app)
- **Backend API:** [HuggingFace Spaces](https://huggingface.co/spaces/sanjana-0809/drone-semantic-search-api)

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and fill in your API keys

# Start the server
uvicorn app.main:app --reload --port 8000
```

Backend runs at: `http://localhost:8000`

### 2. Frontend Setup

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Frontend runs at: `http://localhost:3000`

### 3. Upload & Search

1. Go to `http://localhost:3000`
2. Click the **Upload** tab
3. Drag & drop aerial/drone images
4. Wait ~30–60 seconds for background AI processing
5. Switch to **Search** and start querying!

---

## Environment Variables

**Backend `.env`:**
```env
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_key
CLOUDINARY_CLOUD_NAME=your_name
CLOUDINARY_API_KEY=your_key
CLOUDINARY_API_SECRET=your_secret
ANTHROPIC_API_KEY=sk-ant-...
BASE_URL=http://localhost:8000
```

**Frontend `.env.local`:**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Dataset Sources (No Drone Needed)

| Dataset | Description | Link |
|---------|-------------|------|
| DOTA v1.5 | 2,806 aerial images with object labels | [captain-whu.github.io/DOTA](https://captain-whu.github.io/DOTA) |
| OpenAerialMap | Real licensed drone captures worldwide | [openaerialmap.org](https://openaerialmap.org) |
| USGS Earth Explorer | Free satellite & aerial imagery | [earthexplorer.usgs.gov](https://earthexplorer.usgs.gov) |

> Tip: Download ~100–200 images from one category (vehicles, buildings) for a focused demo.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/upload` | Upload single image (async processing) |
| `POST` | `/upload-batch` | Upload multiple images |
| `POST` | `/search` | Semantic search (`{query, top_k}`) |
| `GET` | `/images-list` | List all indexed images |
| `GET` | `/image/{id}` | Get image detail + AI results |
| `GET` | `/stats` | Collection statistics |
| `POST` | `/generate-report` | Generate site intelligence report |
| `GET` | `/report` | Get latest report |
| `POST` | `/export-report` | Download report as PDF |

---

## Demo Script (4 minutes)

1. **Open the app** → Show landing page with search bar and suggestion chips
2. **Upload** → Switch to Upload tab, drag 5–10 images, show green processing message
3. **Wait** → 30–60 seconds for background AI processing
4. **Search** → Run 3 queries:
   - `"vehicles on road"` → show results grid with similarity scores
   - `"buildings and skyscrapers"` → click a result to show detail modal
   - `"water or river"` → show color swatches and captions
5. **Report** → Click Generate Report, wait for Claude, show formatted report
6. **PDF** → Click Export PDF, open the downloaded file

Total time: ~3–4 minutes

---

## How Search Works

1. Every uploaded image is run through a 5-model AI pipeline:
   - **EasyOCR** → extracts visible text
   - **BLIP** → generates a natural language caption
   - **YOLOv8s** → detects objects
   - **OpenCV K-Means** → extracts dominant colors
   - **CLIP ViT-L/14** → generates a 768-dim semantic embedding

2. The CLIP embedding is stored in **Qdrant** (vector database)

3. At search time, the text query is also embedded with CLIP and compared against all image vectors using **cosine similarity**

4. Query expansion is applied automatically:
   ```
   "roads" → "roads, aerial view, drone footage, roads from above, satellite view of roads"
   ```
   This improves recall for relevant images even when exact words don't match.

---

## Project Structure

```
drone-search-engine/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI routes + async upload
│   │   ├── ai_pipeline.py        # EasyOCR + BLIP + YOLOv8 + OpenCV + CLIP
│   │   ├── database.py           # SQLite database layer
│   │   ├── vector_store.py       # Qdrant vector operations
│   │   ├── cloudinary_helper.py  # Permanent cloud image storage
│   │   └── report_generator.py   # Claude API + PDF export
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── app/
    │   ├── layout.js
    │   ├── page.js
    │   ├── globals.css
    │   └── components/
    │       ├── SearchPage.js
    │       ├── UploadPage.js
    │       └── ReportPage.js
    ├── lib/
    │   └── api.js
    ├── package.json
    └── next.config.js
```

---

## What I'd Improve With More Time

- Change detection between two collections of the same site at different dates — showing construction progress
- Map overlay showing GPS coordinates of each image on a satellite map
- Real-time processing with WebSocket progress updates
- PostgreSQL + pgvector for production-grade data layer
- Authentication and multi-tenant collection management
- GPU support on HF Spaces for faster inference
- Image deduplication using perceptual hashing

---

## Deployment

| Service | What it hosts |
|---------|--------------|
| Hugging Face Spaces (Docker) | FastAPI backend + all AI models |
| Vercel | Next.js frontend |
| Qdrant Cloud | Vector database (free tier) |
| Cloudinary | Image storage (permanent, free tier) |

---

Built by **Sanjana Ghatge**
