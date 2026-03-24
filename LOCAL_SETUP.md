# Running Pratyaksha Locally (Without Docker)

This guide explains how to run all services locally so you can understand what's happening.

## Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- **PostgreSQL 14+**
- **Redis**
- **Milvus** (Vector Database)
- **MinIO** (S3-compatible storage)
- **n8n** (Workflow automation - optional)

## Step 1: Install External Services

### On Windows

#### PostgreSQL
1. Download from https://www.postgresql.org/download/windows/
2. Install with default settings
3. Create user and database:
```sql
CREATE USER pratyaksha WITH PASSWORD 'pratyaksha';
CREATE DATABASE pratyaksha OWNER pratyaksha;
```

#### Redis
1. Download from https://github.com/microsoftarchive/redis/releases
2. Or use WSL: `wsl -- sudo apt-get install redis-server`
3. Start: `redis-server` (default port 6379)

#### Milvus
#Download standalone: https://milvus.io/docs/install_standalone-docker.md
Or use Docker just for this:
```bash
docker run -d -p 19530:19530 -e COMMON_STORAGETYPE=local milvusdb/milvus:latest
```

#### MinIO
#Download from https://min.io/download#/windows
Or use Docker:
```bash
docker run -d -p 9000:9000 -p 9001:9001 minio/minio server /minio_data --console-address ":9001"
```

#### n8n (Optional)
```bash
docker run -d -p 5678:5678 n8nio/n8n
```

Or using npm (if you want to avoid Docker for this too):
```bash
npm install -g n8n
n8n
```

## Step 2: Setup Backend

### 2.1 Navigate to backend directory
```bash
cd backend
```

### 2.2 Create Python virtual environment
```bash
python -m venv venv
```

### 2.3 Activate virtual environment
```bash
# On Windows PowerShell
venv\Scripts\Activate.ps1

# Or on Windows CMD
venv\Scripts\activate.bat
```

### 2.4 Install dependencies
```bash
pip install -r requirements.txt
```

### 2.5 Create .env file
Update the `.env` file in the root directory to use localhost URLs:

```env
DATABASE_URL=postgresql+asyncpg://pratyaksha:pratyaksha@localhost:5432/pratyaksha
REDIS_URL=redis://localhost:6379/0

MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=changeme
MINIO_SECRET_KEY=changeme_secret

MILVUS_HOST=localhost

JWT_SECRET_KEY=supersecretjwtkey
JWT_ALGORITHM=HS256

USE_MOCK_MODELS=true

CORS_ORIGINS=http://localhost:3000,http://localhost:8000

N8N_WEBHOOK_URL=http://localhost:5678/webhook/pratyaksha
```

### 2.6 Run database migrations
```bash
cd ..
alembic -c backend/alembic.ini upgrade head
```

### 2.7 Start the backend server
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000`

## Step 3: Setup Frontend

### 3.1 Navigate to frontend
```bash
cd frontend
```

### 3.2 Install dependencies
```bash
npm install
```

### 3.3 Start development server
```bash
npm run dev
```

Frontend will be available at `http://localhost:3000`

## Step 4: Start Celery Worker (Optional)

For background tasks, open a new terminal:

```bash
cd backend
# Activate venv first
venv\Scripts\Activate.ps1

celery -A workers.celery_app.app worker --loglevel=info
```

## Service Ports Reference

| Service | URL | Default Port |
|---------|-----|--------------|
| Frontend | http://localhost:3000 | 3000 |
| Backend API | http://localhost:8000 | 8000 |
| PostgreSQL | localhost | 5432 |
| Redis | localhost | 6379 |
| Milvus | localhost | 19530 |
| MinIO API | http://localhost:9000 | 9000 |
| MinIO Console | http://localhost:9001 | 9001 |
| n8n | http://localhost:5678 | 5678 |

## Troubleshooting

### Port already in use
Change the port in the startup command:
```bash
uvicorn app.main:app --port 8001
```

### PostgreSQL connection error
Check that:
1. PostgreSQL is running: `psql -U pratyaksha -d pratyaksha`
2. The DATABASE_URL in .env matches your setup
3. User `pratyaksha` exists with password `pratyaksha`

### Redis connection error
Check if Redis is running on port 6379:
```bash
redis-cli ping  # Should return PONG
```

### Missing Python dependencies
Reinstall requirements:
```bash
pip install -r backend/requirements.txt --force-reinstall
```

## Next Steps

- Check `/health` endpoint on the backend to verify services
- Create an admin user: `python backend/scripts/create_admin.py`
- Explore API docs at `http://localhost:8000/docs`
