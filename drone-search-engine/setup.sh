#!/bin/bash
echo "===================================================="
echo " Drone Image Semantic Search Engine — Setup Script"
echo " Skylark Drones Alignment Project"
echo "===================================================="
echo ""

# Check Docker
echo "[1/5] Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "  ERROR: Docker not installed. Install from https://www.docker.com"
    exit 1
fi
echo "  Docker found!"

# Start Qdrant
echo ""
echo "[2/5] Starting Qdrant Vector Database..."
if docker ps -a --format '{{.Names}}' | grep -q qdrant; then
    echo "  Qdrant container exists — starting..."
    docker start qdrant
else
    echo "  Pulling and starting Qdrant..."
    docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant
fi
echo "  Qdrant running at http://localhost:6333/dashboard"

# Backend
echo ""
echo "[3/5] Setting up Python Backend..."
cd backend
if [ ! -d "venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv venv
fi
echo "  Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt --quiet
echo "  Backend ready!"

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  Created .env - add your GROQ_API_KEY and optional Cloudinary keys"
fi
cd ..

# Frontend
echo ""
echo "[4/5] Setting up Next.js Frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "  Installing npm packages..."
    npm install
fi
echo "  Frontend ready!"
cd ..

echo ""
echo "[5/5] Setup Complete!"
echo "===================================================="
echo ""
echo "To start the app, open TWO terminals:"
echo ""
echo "  Terminal 1 (Backend):"
echo "    cd backend && source venv/bin/activate && python run.py"
echo ""
echo "  Terminal 2 (Frontend):"
echo "    cd frontend && npm run dev"
echo ""
echo "Then open http://localhost:3000"
echo "===================================================="
