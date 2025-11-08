# Production Deployment Guide - Data Destroyer

## Overview

This guide covers the complete production deployment of Data Destroyer with:
- Docker containerization for all services
- Automated CI/CD pipeline with GitHub Actions
- Comprehensive monitoring with Prometheus + Grafana
- Automated database and media backups
- SSL/TLS with Nginx reverse proxy
- Health checks and zero-downtime deployments

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │    Nginx    │  (Reverse Proxy + SSL)
                    │   Port 443  │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐      ┌─────▼─────┐    ┌──────▼──────┐
   │ Django  │      │  Celery   │    │ Celery Beat │
   │ Backend │      │  Worker   │    │  Scheduler  │
   └────┬────┘      └─────┬─────┘    └──────┬──────┘
        │                 │                  │
        └────────┬────────┴────────┬─────────┘
                 │                 │
        ┌────────▼────────┐ ┌─────▼────┐
        │   PostgreSQL    │ │  Redis   │
        │   (Database)    │ │ (Cache)  │
        └─────────────────┘ └──────────┘

Monitoring Stack:
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Prometheus  │──│   Grafana    │  │  Node/Redis  │
│   (Metrics)  │  │ (Dashboards) │  │  Exporters   │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Prerequisites

### Server Requirements

**Minimum Specifications:**
- 2 CPU cores
- 4GB RAM
- 40GB SSD storage
- Ubuntu 22.04 LTS or similar

**Recommended for Production:**
- 4+ CPU cores
- 8GB+ RAM
- 100GB+ SSD storage
- Load balancer (for high availability)

### Software Requirements

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installations
docker --version
docker-compose --version
```

## Quick Start Production Deployment

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/datadestroyer.git
cd datadestroyer
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.production.example .env.production

# Edit with your production values
nano .env.production
```

**Critical values to set:**
- `DJANGO_SECRET_KEY`: Generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"`
- `POSTGRES_PASSWORD`: Strong database password
- `GRAFANA_ADMIN_PASSWORD`: Grafana admin password
- `DJANGO_ALLOWED_HOSTS`: Your domain names
- `DJANGO_CSRF_TRUSTED_ORIGINS`: Your HTTPS URLs

### 3. SSL Certificates

**Option A: Let's Encrypt (Recommended)**

```bash
# Install certbot
sudo apt install certbot

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
```

**Option B: Self-Signed (Development Only)**

```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem
```

### 4. Deploy with Docker Compose

**Using Enhanced Stack (with monitoring):**

```bash
# Pull latest images
docker-compose -f docker-compose.prod.enhanced.yml pull

# Start all services
docker-compose -f docker-compose.prod.enhanced.yml up -d

# Check status
docker-compose -f docker-compose.prod.enhanced.yml ps

# View logs
docker-compose -f docker-compose.prod.enhanced.yml logs -f
```

**Using Basic Stack (minimal):**

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 5. Initialize Database

```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Load demo data (optional)
docker-compose exec web python manage.py generate_demo_data --days 30
```

### 6. Verify Deployment

**Health Checks:**
```bash
# Application health
curl https://yourdomain.com/health/

# API health
curl https://yourdomain.com/api/health/

# Metrics
curl https://yourdomain.com/api/metrics/
```

**Access Points:**
- Application: https://yourdomain.com
- Admin: https://yourdomain.com/admin/
- API Docs: https://yourdomain.com/api/docs/
- Grafana: http://yourserver:3000 (admin/password from .env)
- Prometheus: http://yourserver:9090

## CI/CD Pipeline

### GitHub Actions Workflow

The CI/CD pipeline automatically:
1. Runs tests on every push/PR
2. Performs security scans
3. Builds Docker images
4. Pushes to GitHub Container Registry
5. Deploys to production (on main branch)

### Required GitHub Secrets

Navigate to **Settings → Secrets and variables → Actions** and add:

```
DEPLOY_SSH_KEY         # SSH private key for deployment server
DEPLOY_HOST            # Production server hostname
DEPLOY_USER            # SSH username for deployment
GRAFANA_ADMIN_PASSWORD # Grafana password
```

### Deployment Process

```bash
# Automatic deployment on push to main
git push origin main

# Manual deployment
git tag v1.0.0
git push origin v1.0.0
```

## Monitoring and Observability

### Prometheus Metrics

Access: `http://yourserver:9090`

**Available Metrics:**
- `django_*` - Django application metrics
- `postgres_*` - Database metrics
- `redis_*` - Cache metrics
- `node_*` - System metrics

**Example Queries:**
```promql
# Request rate
rate(django_http_requests_total[5m])

# Error rate
rate(django_http_responses_total{status="500"}[5m])

# Database connections
postgres_stat_database_numbackends

# Cache hit rate
rate(redis_keyspace_hits_total[5m]) / rate(redis_keyspace_misses_total[5m])
```

### Grafana Dashboards

Access: `http://yourserver:3000` (admin/password from .env)

**Pre-configured Dashboards:**
1. **Application Performance**
   - Request rates and latency
   - Error rates
   - Response times

2. **Infrastructure**
   - CPU, memory, disk usage
   - Network traffic
   - Container health

3. **Business Metrics**
   - Active users
   - Data classifications
   - Policy violations

**Import Community Dashboards:**
```
Django Dashboard: 9528
PostgreSQL: 9628
Redis: 763
Node Exporter: 1860
```

## Backup and Disaster Recovery

### Automated Backups

**Database Backups (Daily):**

```bash
# Manual backup
./scripts/backup/backup-database.sh

# Setup cron job (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /path/to/datadestroyer/scripts/backup/backup-database.sh
```

**Media Files Backup (Weekly):**

```bash
# Manual backup
./scripts/backup/backup-media.sh

# Setup cron job (weekly on Sunday at 3 AM)
# Add: 0 3 * * 0 /path/to/datadestroyer/scripts/backup/backup-media.sh
```

### S3 Backup Configuration

```bash
# Configure AWS CLI
aws configure

# Enable S3 backups in .env.production
AWS_S3_BACKUP_BUCKET=destroyer-backups
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

### Restore Procedures

**Database Restore:**

```bash
# Stop services
docker-compose stop web celery celery-beat

# Restore from backup
gunzip -c /backups/postgres/destroyer_db_TIMESTAMP.sql.gz | \
  docker-compose exec -T db psql -U destroyer -d postgres

# Restart services
docker-compose start web celery celery-beat
```

**Media Files Restore:**

```bash
# From local backup
tar -xzf /backups/media/destroyer_media_TIMESTAMP.tar.gz -C ./media/

# From S3
aws s3 sync s3://destroyer-backups/media/ ./media/
```

## Security Best Practices

### 1. Environment Variables

```bash
# Secure .env file permissions
chmod 600 .env.production

# Never commit .env to git
echo ".env.production" >> .gitignore
```

### 2. Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### 3. SSL/TLS Best Practices

- Use Let's Encrypt for free SSL certificates
- Enable HTTP/2 in Nginx
- Set HSTS headers (already configured)
- A+ rating on SSL Labs: https://www.ssllabs.com/ssltest/

### 4. Regular Updates

```bash
# Update Docker images monthly
docker-compose pull
docker-compose up -d

# Update system packages
sudo apt update && sudo apt upgrade -y
```

### 5. Security Scanning

```bash
# Scan for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image ghcr.io/yourusername/datadestroyer:latest
```

## Performance Optimization

### Database Optimization

```python
# In Django settings
DATABASES = {
    'default': {
        # ...
        'CONN_MAX_AGE': 600,  # Connection pooling
    }
}
```

### Caching Strategy

```python
# Configure Redis caching
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/0',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### Load Testing

```bash
# Install load testing tool
pip install locust

# Run load test
locust -f locustfile.py --host=https://yourdomain.com
```

## Scaling Guide

### Horizontal Scaling

**Add more web workers:**

```yaml
# docker-compose.prod.enhanced.yml
web:
  deploy:
    replicas: 3
```

**Load balancer configuration:**

```nginx
upstream django_backend {
    server web1:8000;
    server web2:8000;
    server web3:8000;
}
```

### Database Scaling

**Read Replicas:**

```python
DATABASES = {
    'default': {...},  # Primary (write)
    'replica': {...},  # Read replica
}
```

## Troubleshooting

### Common Issues

**1. Container won't start:**

```bash
# Check logs
docker-compose logs web

# Inspect container
docker inspect destroyer-backend

# Shell into container
docker-compose exec web bash
```

**2. Database connection errors:**

```bash
# Check database is running
docker-compose ps db

# Test connection
docker-compose exec db psql -U destroyer -d destroyer
```

**3. Static files not loading:**

```bash
# Recollect static files
docker-compose exec web python manage.py collectstatic --clear --noinput

# Check Nginx configuration
docker-compose exec nginx nginx -t
```

### Health Check Endpoints

```bash
# Comprehensive health check
curl https://yourdomain.com/health/
# Returns: {"status": "healthy", "checks": {...}}

# Readiness check
curl https://yourdomain.com/ready/
# Returns: {"status": "ready"}

# Liveness check
curl https://yourdomain.com/alive/
# Returns: {"status": "alive"}
```

## Maintenance

### Zero-Downtime Deployments

```bash
# Pull new images
docker-compose pull

# Recreate containers one at a time
docker-compose up -d --no-deps --scale web=2 web
docker-compose up -d --no-deps --scale web=1 web
```

### Database Migrations

```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Rollback migration
docker-compose exec web python manage.py migrate app_name 0001
```

### Log Management

```bash
# View logs
docker-compose logs -f --tail=100 web

# Rotate logs
docker-compose logs --no-log-prefix web > logs/web-$(date +%Y%m%d).log

# Clear logs
truncate -s 0 $(docker inspect --format='{{.LogPath}}' destroyer-backend)
```

## Success Metrics

**Production Readiness Checklist:**

- [ ] SSL/TLS configured (A+ rating)
- [ ] Health checks passing
- [ ] Automated backups configured
- [ ] Monitoring dashboards set up
- [ ] CI/CD pipeline working
- [ ] Firewall configured
- [ ] Environment variables secured
- [ ] Database migrations applied
- [ ] Static files serving correctly
- [ ] Error tracking configured (Sentry)
- [ ] Load testing completed
- [ ] Disaster recovery tested

**Performance Targets:**

- 99.9% uptime
- < 500ms average response time
- < 2s database query time
- 95%+ cache hit rate
- Zero critical security vulnerabilities

## Support

For issues or questions:
- GitHub Issues: https://github.com/yourusername/datadestroyer/issues
- Documentation: https://docs.yourdomain.com
- Email: support@yourdomain.com

---

**Version**: 1.0.0
**Last Updated**: 2025-11-08
**Status**: Production Ready ✅
