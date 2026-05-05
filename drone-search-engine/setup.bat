@echo off
echo ====================================================
echo  Drone Image Semantic Search Engine — Setup Script
echo  Skylark Drones Alignment Project
echo ====================================================
echo.

:: Check Docker is running
echo [1/5] Checking Docker...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not running.
    echo Install Docker Desktop from https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)
echo       Docker found!

:: Start Qdrant
echo.
echo [2/5] Starting Qdrant Vector Database...
docker ps -a --format "{{.Names}}" | findstr /i "qdrant" >nul 2>&1
if %errorlevel% equ 0 (
    echo       Qdrant container exists — starting it...
    docker start qdrant
) else (
    echo       Pulling and starting Qdrant...
    docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant
)
echo       Qdrant running at http://localhost:6333/dashboard

:: Backend setup
echo.
echo [3/5] Setting up Python Backend...
cd backend
if not exist venv (
    echo       Creating virtual environment...
    python -m venv venv
)
echo       Activating venv and installing dependencies...
call venv\Scripts\activate
pip install -r requirements.txt --quiet
echo       Backend dependencies installed!

:: Check .env
if not exist .env (
    echo.
    echo WARNING: No .env file found!
    echo Copy .env.example to .env and add your GROQ_API_KEY
    copy .env.example .env
    echo       Created .env from template - edit it with your API keys
)

cd ..

:: Frontend setup
echo.
echo [4/5] Setting up Next.js Frontend...
cd frontend
if not exist node_modules (
    echo       Installing npm packages...
    npm install
)
echo       Frontend dependencies installed!
cd ..

echo.
echo [5/5] Setup Complete!
echo ====================================================
echo.
echo To start the app, open TWO terminals:
echo.
echo   Terminal 1 (Backend):
echo     cd backend
echo     venv\Scripts\activate
echo     python run.py
echo.
echo   Terminal 2 (Frontend):
echo     cd frontend
echo     npm run dev
echo.
echo Then open http://localhost:3000 in your browser.
echo ====================================================
pause
