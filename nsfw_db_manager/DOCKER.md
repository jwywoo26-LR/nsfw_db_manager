# 🐳 Docker Deployment Guide

Deploy the NSFW Image Asset Manager using Docker Compose.

## Prerequisites

- Docker installed
- Docker Compose installed

## Quick Start

```bash
# 1. Navigate to the project directory
cd nsfw_db_manager

# 2. Build and start all services
docker-compose up -d

# 3. Check status
docker-compose ps

# 4. View logs
docker-compose logs -f
```

That's it! The services will be available at:
- **Backend API**: http://localhost:8001
- **Frontend UI**: http://localhost:7860
- **API Docs**: http://localhost:8001/docs

## Services

### Backend (FastAPI)
- **Port**: 8001
- **Storage**: Local file storage in `backend/uploads/`
- **Database**: SQLite in `backend/nsfw_assets.db`
- **Health Check**: http://localhost:8001/api/health

### Frontend (Gradio)
- **Port**: 7860
- **Connects to**: Backend service automatically

## Configuration

### Environment Variables

Edit `docker-compose.yml` to configure:

```yaml
environment:
  - USE_LOCAL_STORAGE=true
  - LOCAL_UPLOAD_DIR=uploads/images
  - DATABASE_URL=sqlite:///./nsfw_assets.db
```

### Volumes

Data is persisted in:
- `./backend/uploads` - Uploaded images
- `./backend/nsfw_assets.db` - SQLite database

## Common Commands

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### View Logs
```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Frontend only
docker-compose logs -f frontend
```

### Rebuild After Code Changes
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Access Container Shell
```bash
# Backend
docker-compose exec backend /bin/bash

# Frontend
docker-compose exec frontend /bin/bash
```

### Check Service Status
```bash
docker-compose ps
```

## Troubleshooting

### Backend won't start
```bash
# Check logs
docker-compose logs backend

# Restart backend
docker-compose restart backend
```

### Frontend can't connect to backend
```bash
# Check if backend is healthy
curl http://localhost:8001/api/health

# Restart both services
docker-compose restart
```

### Database issues
```bash
# Stop services
docker-compose down

# Remove database (WARNING: deletes all data)
rm backend/nsfw_assets.db

# Start fresh
docker-compose up -d
```

### Port already in use
```bash
# Change ports in docker-compose.yml
ports:
  - "8002:8001"  # Map to different host port
```

## Production Deployment

### Using AWS S3 (Optional)

1. Update `docker-compose.yml`:
```yaml
environment:
  - USE_LOCAL_STORAGE=false
  - AWS_ACCESS_KEY_ID=your_key
  - AWS_SECRET_ACCESS_KEY=your_secret
  - AWS_DEFAULT_REGION=ap-northeast-2
  - S3_BUCKET=your-bucket
```

2. Restart services:
```bash
docker-compose down
docker-compose up -d
```

### Using PostgreSQL (Optional)

1. Add PostgreSQL service to `docker-compose.yml`:
```yaml
services:
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=nsfw_assets
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/nsfw_assets
    depends_on:
      - postgres

volumes:
  postgres_data:
```

2. Update backend requirements to include:
```
psycopg2-binary>=2.9.0
```

3. Rebuild:
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

## Backup & Restore

### Backup
```bash
# Backup database
cp backend/nsfw_assets.db backend/nsfw_assets.db.backup

# Backup uploads
tar -czf uploads_backup.tar.gz backend/uploads/
```

### Restore
```bash
# Restore database
cp backend/nsfw_assets.db.backup backend/nsfw_assets.db

# Restore uploads
tar -xzf uploads_backup.tar.gz
```

## Monitoring

### Check resource usage
```bash
docker stats
```

### View container details
```bash
docker-compose ps
docker inspect nsfw-backend
docker inspect nsfw-frontend
```

## Cleanup

### Remove containers but keep data
```bash
docker-compose down
```

### Remove everything including volumes
```bash
docker-compose down -v
```

### Remove images
```bash
docker-compose down --rmi all
```

## Network

Services communicate on internal Docker network:
- Frontend → Backend: `http://backend:8001`
- Host → Backend: `http://localhost:8001`
- Host → Frontend: `http://localhost:7860`

## Security Notes

- Default setup uses SQLite and local storage (good for development)
- For production: Use PostgreSQL and S3
- Consider adding nginx reverse proxy for SSL
- Set proper firewall rules for exposed ports
- Use environment files for secrets (not hardcoded in docker-compose.yml)

## Next Steps

1. ✅ Start services with `docker-compose up -d`
2. ✅ Open http://localhost:7860 for the UI
3. ✅ Upload some images to test
4. ✅ Check http://localhost:8001/docs for API documentation
