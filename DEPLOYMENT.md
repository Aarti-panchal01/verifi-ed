# VerifiedProtocol — Production Deployment Guide

## 🎯 Overview

This guide covers deploying VerifiedProtocol to production environments.

## 📋 Pre-Deployment Checklist

### Infrastructure Requirements
- [ ] Python 3.10+ runtime environment
- [ ] Node.js 18+ for frontend
- [ ] PostgreSQL or similar (optional, for caching)
- [ ] Redis (optional, for rate limiting)
- [ ] SSL/TLS certificates
- [ ] Domain name configured
- [ ] Algorand node access (or use public API)

### Security Requirements
- [ ] Environment variables secured (never commit .env)
- [ ] API keys rotated and stored in secrets manager
- [ ] Rate limiting configured
- [ ] CORS properly configured for production domains
- [ ] Logging configured (no sensitive data in logs)
- [ ] Error messages sanitized (no stack traces to clients)

### Performance Requirements
- [ ] Database connection pooling configured
- [ ] CDN configured for static assets
- [ ] Caching strategy implemented
- [ ] Load balancer configured (if multi-instance)
- [ ] Health check endpoints tested

## 🚀 Backend Deployment

### Option 1: Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ALGOD_SERVER=${ALGOD_SERVER}
      - ALGOD_PORT=${ALGOD_PORT}
      - ALGOD_TOKEN=${ALGOD_TOKEN}
      - DEPLOYER_MNEMONIC=${DEPLOYER_MNEMONIC}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Option 2: Traditional Server Deployment

```bash
# 1. Clone repository
git clone <repository-url>
cd verified_protocol

# 2. Install dependencies
poetry install --no-dev

# 3. Configure environment
cp .env.example .env
# Edit .env with production values

# 4. Run with gunicorn (production WSGI server)
poetry run gunicorn backend.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile /var/log/verified-protocol/access.log \
  --error-logfile /var/log/verified-protocol/error.log
```

### Option 3: Cloud Platform Deployment

#### AWS Elastic Beanstalk
```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p python-3.10 verified-protocol

# Create environment
eb create verified-protocol-prod

# Deploy
eb deploy
```

#### Google Cloud Run
```bash
# Build container
gcloud builds submit --tag gcr.io/PROJECT_ID/verified-protocol

# Deploy
gcloud run deploy verified-protocol \
  --image gcr.io/PROJECT_ID/verified-protocol \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### Heroku
```bash
# Create app
heroku create verified-protocol

# Set environment variables
heroku config:set ALGOD_SERVER=...
heroku config:set ALGOD_TOKEN=...
heroku config:set DEPLOYER_MNEMONIC=...

# Deploy
git push heroku main
```

## 🌐 Frontend Deployment

### Build for Production

```bash
cd frontend

# Install dependencies
npm install

# Build
npm run build

# Output will be in dist/
```

### Option 1: Static Hosting (Vercel, Netlify, etc.)

#### Vercel
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

#### Netlify
```bash
# Install Netlify CLI
npm i -g netlify-cli

# Deploy
netlify deploy --prod --dir=dist
```

### Option 2: CDN + Object Storage

```bash
# AWS S3 + CloudFront
aws s3 sync dist/ s3://your-bucket-name/
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"

# Google Cloud Storage + CDN
gsutil -m rsync -r dist/ gs://your-bucket-name/
```

### Option 3: Traditional Web Server

```nginx
# nginx.conf
server {
    listen 80;
    server_name your-domain.com;

    root /var/www/verified-protocol/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🔧 Environment Configuration

### Backend (.env)

```bash
# Algorand Configuration
ALGOD_SERVER=https://testnet-api.algonode.cloud
ALGOD_PORT=443
ALGOD_TOKEN=
DEPLOYER_MNEMONIC=your-25-word-mnemonic-here

# Application Configuration
APP_ENV=production
LOG_LEVEL=INFO
RATE_LIMIT=60
RATE_WINDOW=60

# Optional: Database
DATABASE_URL=postgresql://user:pass@localhost/verified_protocol

# Optional: Redis
REDIS_URL=redis://localhost:6379/0

# Optional: Monitoring
SENTRY_DSN=https://...
```

### Frontend (.env.production)

```bash
VITE_API_URL=https://api.your-domain.com
VITE_NETWORK=testnet
VITE_APP_NAME=VerifiedProtocol
VITE_APP_VERSION=2.0.0
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_DEBUG=false
```

## 📊 Monitoring & Logging

### Application Monitoring

```python
# backend/main.py - Add Sentry integration
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
    environment=os.getenv("APP_ENV", "production"),
)
```

### Logging Configuration

```python
# backend/logging_config.py
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "json",
            "filename": "/var/log/verified-protocol/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"],
    },
}
```

### Health Checks

```python
# backend/routers/health.py
from fastapi import APIRouter
import time

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": int(time.time()),
        "version": "2.0.0",
    }

@router.get("/health/detailed")
async def detailed_health():
    # Check Algorand connectivity
    try:
        manager = get_manager()
        algo_status = "connected"
    except Exception:
        algo_status = "disconnected"
    
    return {
        "status": "healthy" if algo_status == "connected" else "degraded",
        "components": {
            "algorand": algo_status,
            "api": "operational",
        },
        "timestamp": int(time.time()),
    }
```

## 🔒 Security Hardening

### 1. Environment Variables
```bash
# Never commit .env files
# Use secrets manager in production
aws secretsmanager create-secret --name verified-protocol/deployer-mnemonic --secret-string "..."
```

### 2. CORS Configuration
```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # Specific domains only
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### 3. Rate Limiting (Redis-based)
```python
# backend/middleware/rate_limit.py
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis

@app.on_event("startup")
async def startup():
    redis_client = redis.from_url("redis://localhost")
    await FastAPILimiter.init(redis_client)

@app.get("/api/endpoint", dependencies=[Depends(RateLimiter(times=60, seconds=60))])
async def endpoint():
    pass
```

### 4. Input Validation
```python
# All inputs validated via Pydantic models
from pydantic import BaseModel, Field, validator

class SubmitRequest(BaseModel):
    skill_id: str = Field(..., min_length=1, max_length=100)
    score: int = Field(..., ge=0, le=100)
    
    @validator('skill_id')
    def validate_skill_id(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Invalid skill_id format')
        return v
```

## 📈 Performance Optimization

### 1. Database Connection Pooling
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
)
```

### 2. Caching
```python
from functools import lru_cache
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

@app.on_event("startup")
async def startup():
    redis_client = aioredis.from_url("redis://localhost")
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")

@router.get("/reputation/{wallet}")
@cache(expire=300)  # Cache for 5 minutes
async def get_reputation(wallet: str):
    pass
```

### 3. Async Operations
```python
# Use async/await for I/O operations
import asyncio

async def fetch_multiple_records(wallets: list[str]):
    tasks = [service.get_skill_records(w) for w in wallets]
    return await asyncio.gather(*tasks)
```

## 🧪 Pre-Production Testing

```bash
# 1. Run all tests
poetry run pytest

# 2. Load testing
poetry run locust -f tests/load_test.py --host=http://localhost:8000

# 3. Security scanning
poetry run bandit -r backend/

# 4. Dependency audit
poetry run safety check

# 5. Code quality
poetry run pylint backend/
poetry run mypy backend/
```

## 📝 Deployment Checklist

- [ ] All tests passing
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] SSL certificates installed
- [ ] CORS configured for production domains
- [ ] Rate limiting enabled
- [ ] Logging configured
- [ ] Monitoring/alerting set up
- [ ] Health checks working
- [ ] Backup strategy implemented
- [ ] Rollback plan documented
- [ ] Load testing completed
- [ ] Security audit completed
- [ ] Documentation updated
- [ ] Team notified of deployment

## 🔄 Continuous Deployment

### GitHub Actions Example

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      
      - name: Run tests
        run: poetry run pytest
      
      - name: Deploy to production
        run: |
          # Your deployment script here
          ./deploy.sh
        env:
          ALGOD_SERVER: ${{ secrets.ALGOD_SERVER }}
          DEPLOYER_MNEMONIC: ${{ secrets.DEPLOYER_MNEMONIC }}
```

## 🆘 Troubleshooting

### Common Issues

1. **Connection timeout to Algorand**
   - Check ALGOD_SERVER and ALGOD_TOKEN
   - Verify network connectivity
   - Check rate limits

2. **High memory usage**
   - Reduce worker count
   - Enable connection pooling
   - Implement caching

3. **Slow API responses**
   - Enable caching
   - Optimize database queries
   - Use async operations

4. **Rate limit errors**
   - Increase rate limits
   - Implement request queuing
   - Use Redis for distributed rate limiting

---

**For support, open an issue on the repository.**
