# Quick Start Script for Pratyaksha (Local Setup)
# Run this script to automate the initial setup

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Pratyaksha - Local Development Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "Checking Python..." -ForegroundColor Yellow
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Check Node.js
Write-Host "Checking Node.js..." -ForegroundColor Yellow
node --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Node.js not found. Please install Node.js 20+" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✓ Prerequisites OK" -ForegroundColor Green
Write-Host ""

# Backend Setup
Write-Host "Setting up Backend..." -ForegroundColor Yellow
cd backend

Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
python -m venv venv

Write-Host "Activating virtual environment..." -ForegroundColor Cyan
.\venv\Scripts\Activate.ps1

Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

cd ..

# Database Migrations
Write-Host ""
Write-Host "Running database migrations..." -ForegroundColor Yellow
Write-Host "(Make sure PostgreSQL is running!)" -ForegroundColor Yellow
alembic -c backend/alembic.ini upgrade head

# Frontend Setup
Write-Host ""
Write-Host "Setting up Frontend..." -ForegroundColor Yellow
cd frontend

Write-Host "Installing Node dependencies..." -ForegroundColor Cyan
npm install

cd ..

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Make sure these services are running:" -ForegroundColor White
Write-Host "   - PostgreSQL (port 5432)" -ForegroundColor Gray
Write-Host "   - Redis (port 6379)" -ForegroundColor Gray
Write-Host "   - Milvus (port 19530)" -ForegroundColor Gray
Write-Host "   - MinIO (ports 9000, 9001)" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Start Backend:" -ForegroundColor Cyan
Write-Host "   cd backend" -ForegroundColor Gray
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "   uvicorn app.main:app --reload" -ForegroundColor Gray
Write-Host ""
Write-Host "3. In another terminal, start Frontend:" -ForegroundColor Cyan
Write-Host "   cd frontend" -ForegroundColor Gray
Write-Host "   npm run dev" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Access the app:" -ForegroundColor Cyan
Write-Host "   Frontend: http://localhost:3000" -ForegroundColor Gray
Write-Host "   API: http://localhost:8000" -ForegroundColor Gray
Write-Host "   API Docs: http://localhost:8000/docs" -ForegroundColor Gray
Write-Host ""
