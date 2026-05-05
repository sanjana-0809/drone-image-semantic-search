---
title: Drone Semantic Search API
colorFrom: blue
colorTo: cyan
sdk: docker
pinned: false
---

# Drone Semantic Search API

FastAPI backend for validated drone-image uploads, AI processing, Qdrant indexing, semantic search, and Groq-powered site intelligence reports.

Required runtime services:

- Qdrant, either local at `QDRANT_HOST`/`QDRANT_PORT` or cloud via `QDRANT_URL`.
- `GROQ_API_KEY` for report generation.
- Cloudinary credentials only if permanent cloud image delivery is needed.
