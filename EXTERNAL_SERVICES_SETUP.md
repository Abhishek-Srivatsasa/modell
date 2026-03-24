# External Services Setup Checklist

This checklist helps you get all the required services running locally.

## Required Services

### 1. PostgreSQL Database
- [ ] Download: https://www.postgresql.org/download/windows/
- [ ] Install with default options
- [ ] Create user: `pratyaksha` with password `pratyaksha`
- [ ] Create database: `pratyaksha`
- [ ] Verify connection: `psql -U pratyaksha -d pratyaksha`
- **Port**: 5432

**Quick setup in pgAdmin:**
```sql
CREATE USER pratyaksha WITH PASSWORD 'pratyaksha';
CREATE DATABASE pratyaksha OWNER pratyaksha;
GRANT ALL PRIVILEGES ON DATABASE pratyaksha TO pratyaksha;
```

### 2. Redis
- [ ] Download: https://github.com/microsoftarchive/redis/releases
- [ ] Extract and add to PATH (optional)
- [ ] Start: `redis-server`
- [ ] Verify: `redis-cli ping` (should return PONG)
- **Port**: 6379

**Alternative (using WSL):**
```bash
wsl -- sudo apt-get install redis-server
wsl -- redis-server
```

### 3. Milvus (Vector Database)
- **Easiest option**: Use Docker (even if removing Docker elsewhere):
```bash
docker run -d -p 19530:19530 -e COMMON_STORAGETYPE=local milvusdb/milvus:latest
```

- **Alternative**: Download standalone from https://milvus.io/docs/install_standalone-docker.md
- **Port**: 19530

### 4. MinIO (S3-compatible Storage)
- **Easy option**: Use Docker:
```bash
docker run -d -p 9000:9000 -p 9001:9001 minio/minio server /minio_data --console-address ":9001"
```

- **Alternative**: Download from https://min.io/download#/windows
- **Ports**: 9000 (API), 9001 (Console)
- **Access**: http://localhost:9001 (login with default creds or update in .env)

### 5. n8n (Workflow Automation - Optional)
- **Using Docker**:
```bash
docker run -d -p 5678:5678 n8nio/n8n
```

- **Using npm**:
```bash
npm install -g n8n
n8n
```

- **Port**: 5678
- **Access**: http://localhost:5678

## Verification Checklist

Run these commands to verify services are running:

```powershell
# PostgreSQL
psql -U pratyaksha -d pratyaksha -c "SELECT version();"

# Redis
redis-cli ping

# Milvus (from Python)
python -c "from pymilvus import connections; connections.connect('default', host='localhost', port=19530); print('Milvus OK')"

# MinIO
curl http://localhost:9000

# n8n
curl http://localhost:5678
```

## Environment Variables

The `.env` file has been updated with localhost URLs:
- ✓ DATABASE_URL points to localhost
- ✓ REDIS_URL points to localhost
- ✓ MINIO_ENDPOINT points to localhost
- ✓ MILVUS_HOST points to localhost
- ✓ All service URLs use 127.0.0.1 or localhost

## Common Issues

### "Connection refused" on backend startup
**Solution**: Ensure PostgreSQL and Redis are running
```powershell
# Check PostgreSQL
psql -U pratyaksha -d pratyaksha

# Check Redis
redis-cli ping
```

### Port already in use
**Solution**: Change the port in the startup command
```bash
# Instead of default port 8000
uvicorn app.main:app --port 8001
```

### "No module named 'app'"
**Solution**: Make sure you're in the backend directory and venv is activated
```bash
cd backend
.\venv\Scripts\Activate.ps1
```

## Starting Services Order

1. **Start external services first** (PostgreSQL, Redis, Milvus, MinIO)
2. **Then start backend** (FastAPI server)
3. **Then start frontend** (Next.js)
4. **Optional**: Start Celery worker for background tasks

## Quick Start Command

After services are running, in the project root:

```powershell
# Terminal 1 - Backend
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload

# Terminal 2 - Frontend  
cd frontend
npm run dev

# Terminal 3 - Celery (optional)
cd backend
.\venv\Scripts\Activate.ps1
celery -A workers.celery_app.app worker --loglevel=info
```

## Access Points

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |
| n8n | http://localhost:5678 |

---

✓ All Docker dependencies removed - you now have full transparency over what's running!
