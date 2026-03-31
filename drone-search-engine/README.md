# Drone Image Semantic Search Engine

**AI-powered search through aerial drone imagery using natural language queries.**

Built as an alignment project for Skylark Drones — demonstrating skills in aerial image AI, vector search, and automated site reporting that mirror Skylark's Spectra platform.

---

## What It Does

Upload drone/aerial images → AI processes each one (caption, object detection, OCR, color analysis) → Search the collection using plain English → Generate a Site Intelligence Report with Claude API → Export as PDF.

**Example queries:**
- `"construction site with cranes"`
- `"vehicles on road"`
- `"water body near buildings"`
- `"solar panels on rooftop"`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI (Python) |
| **Frontend** | Next.js 14 (App Router) + Tailwind CSS |
| **Image Captioning** | BLIP-2 base (Salesforce) |
| **Object Detection** | YOLOv8 nano (Ultralytics) |
| **Text Extraction** | EasyOCR |
| **Color Analysis** | OpenCV + K-means |
| **Embeddings** | CLIP ViT-B/32 (OpenCLIP) |
| **Vector Search** | Qdrant |
| **Report Generation** | Claude API (Anthropic) |
| **PDF Export** | ReportLab |
| **Database** | SQLite (dev) / PostgreSQL (prod) |

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker (for Qdrant)

### 1. Start Qdrant Vector Database
```bash
docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant
```

### 2. Backend Setup
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
# Edit .env and add your ANTHROPIC_API_KEY

# Start the server
python run.py
```
Backend runs at: **http://localhost:8000**

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```
Frontend runs at: **http://localhost:3000**

### 4. Upload Images
- Go to http://localhost:3000
- Click the **Upload** tab
- Drag & drop aerial/drone images (or browse)
- Wait for AI processing (each image takes ~5-15 seconds)
- Switch to **Search** and start querying!

---

## Dataset Sources (No Drone Needed)

| Dataset | Description | Link |
|---------|-------------|------|
| DOTA v1.5 | 2,806 aerial images with object labels | [captain-whu.github.io/DOTA](https://captain-whu.github.io/DOTA) |
| OpenAerialMap | Real licensed drone captures worldwide | [openaerialmap.org](https://openaerialmap.org) |
| USGS Earth Explorer | Free satellite & aerial imagery | [earthexplorer.usgs.gov](https://earthexplorer.usgs.gov) |

**Tip:** Download ~100-200 images from one category (vehicles, buildings) for a focused demo.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload` | Upload single image |
| POST | `/upload-batch` | Upload multiple images |
| POST | `/search` | Semantic search (JSON body: `{query, top_k}`) |
| GET | `/images-list` | List all indexed images |
| GET | `/image/{id}` | Get image detail |
| GET | `/stats` | Collection statistics |
| POST | `/generate-report` | Generate site intelligence report |
| GET | `/report` | Get latest report |
| POST | `/export-report` | Download report as PDF |
| GET | `/health` | Health check |

---

## Demo Script (4 minutes)

1. **Open the app** → Show landing page with search bar
2. **Upload** → Switch to Upload tab, drag 5-10 images, show AI processing progress
3. **Search** → Run 3 queries:
   - `"vehicles on road"` → show results grid
   - `"buildings with shadows"` → click a result to show detail modal
   - `"water or river"` → show similarity scores
4. **Report** → Click Generate Report, wait for Claude, show formatted report
5. **PDF** → Click Export PDF, open the downloaded file
6. **Done** → Total time: ~3-4 minutes

---

## Project Structure

```
drone-search-engine/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI routes
│   │   ├── ai_pipeline.py       # EasyOCR + BLIP-2 + YOLOv8 + OpenCV + CLIP
│   │   ├── database.py          # SQLite database layer
│   │   ├── vector_store.py      # Qdrant vector operations
│   │   └── report_generator.py  # Claude API + PDF export
│   ├── images/                  # Uploaded images stored here
│   ├── reports/                 # Generated PDFs
│   ├── requirements.txt
│   ├── run.py
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── layout.js
│   │   ├── page.js
│   │   ├── globals.css
│   │   └── components/
│   │       ├── SearchPage.js
│   │       ├── UploadPage.js
│   │       └── ReportPage.js
│   ├── lib/
│   │   └── api.js
│   ├── package.json
│   ├── next.config.js
│   └── tailwind.config.js
└── README.md
```

---

## What I'd Improve With More Time

- **Change detection** between two collections of the same site at different dates — showing construction progress
- **Map overlay** showing GPS coordinates of each image on a satellite map
- **Real-time processing** with WebSocket progress updates
- **PostgreSQL + Redis** for production-grade data layer
- **Authentication** and multi-tenant collection management

---

## Skylark Alignment

This project demonstrates domain skills directly relevant to Skylark Drones:

- **Spectra Reporting** → Auto-generated insight reports mirror Spectra's site progress reports
- **Aerial Image Understanding** → CLIP + BLIP-2 pipeline processes drone captures
- **Enterprise Retrieval** → Vector search over thousands of images at scale
- **Domain Data** → Built with real aerial datasets (DOTA, OpenAerialMap)

---

Built by Sanjay · Skylark Drones Alignment Project
