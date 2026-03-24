@echo off
REM Start Backend
start "Backend - FastAPI" cmd /k "cd backend && venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

REM Start Frontend
start "Frontend - Next.js" cmd /k "cd frontend && npm run dev"

REM Start Celery Worker (optional)
echo.
echo NOTE: To start Celery worker for background tasks, open another terminal and run:
echo cd backend 
echo venv\Scripts\activate.bat
echo celery -A workers.celery_app.app worker --loglevel=info
echo.

echo Starting services...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
