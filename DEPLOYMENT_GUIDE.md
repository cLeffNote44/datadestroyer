# Data Destroyer - Quick Deployment Guide

## Overview

This guide provides a streamlined approach to deploying Data Destroyer to production. For comprehensive documentation, see [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md).

## Prerequisites

Before deploying, ensure you have:
- A production server (Ubuntu 22.04 LTS recommended)
- Docker and Docker Compose installed
- Domain name configured (DNS pointing to your server)
- SSH access to the production server
- Minimum 4GB RAM, 2 CPU cores, 40GB storage

## Quick Deployment (5 Steps)

### Step 1: Clone the Repository

```bash
# On your production server
git clone https://github.com/yourusername/datadestroyer.git
cd datadestroyer

# Or pull the latest changes if already cloned
git pull origin main
```

### Step 2: Run Automated Deployment

The automated deployment script will guide you through the entire setup:

```bash
./scripts/deploy/deploy-production.sh
```

This script will:
- ✅ Check prerequisites (Docker, Docker Compose)
- ✅ Configure environment variables (.env.production)
- ✅ Set up SSL certificates
- ✅ Pull/build Docker images
- ✅ Deploy all services (PostgreSQL, Redis, Django, Celery, Nginx, Prometheus, Grafana)
- ✅ Run database migrations
- ✅ Collect static files
- ✅ Create superuser account
- ✅ Set up automated backups

**Follow the prompts** - the script will ask for:
- Domain name
- SSL certificate choice (Let's Encrypt recommended)
- Whether to load demo data
- Whether to set up automated backups

### Step 3: Verify Deployment

After deployment completes, run the verification script:

```bash
./scripts/deploy/verify-deployment.sh
```

This will check:
- ✅ All Docker services are running
- ✅ Health endpoints are responding
- ✅ Database connectivity
- ✅ SSL certificates
- ✅ Monitoring stack (Prometheus, Grafana)
- ✅ Backup configuration
- ✅ Security settings

### Step 4: Access the Platform

Once verified, access your deployment:

**Application URLs:**
- Main Application: `https://yourdomain.com`
- Admin Panel: `https://yourdomain.com/admin/`
- API Documentation: `https://yourdomain.com/api/docs/`

**Monitoring:**
- Grafana Dashboards: `http://yourserver:3000` (user: admin, password from .env)
- Prometheus Metrics: `http://yourserver:9090`

**Health Checks:**
- Comprehensive: `https://yourdomain.com/health/`
- Readiness: `https://yourdomain.com/ready/`
- Liveness: `https://yourdomain.com/alive/`
- Metrics: `https://yourdomain.com/api/metrics/`

### Step 5: Configure Monitoring

Import Grafana dashboards for visualization:

1. Access Grafana at `http://yourserver:3000`
2. Login with credentials from `.env.production`
3. Go to **Dashboards** → **Import**
4. Import community dashboards:
   - Django Application: **9528**
   - PostgreSQL: **9628**
   - Redis: **763**
   - Node Exporter: **1860**

## Manual Deployment (Alternative)

If you prefer manual deployment, follow these steps:

### 1. Configure Environment

```bash
# Copy environment template
cp .env.production.example .env.production

# Edit with your values
nano .env.production
```

**Required values:**
- `DJANGO_SECRET_KEY` - Generate with: `python -c "import secrets; print(secrets.token_urlsafe(50))"`
- `POSTGRES_PASSWORD` - Strong database password
- `GRAFANA_ADMIN_PASSWORD` - Grafana admin password
- `DJANGO_ALLOWED_HOSTS` - Your domain names (comma-separated)
- `DJANGO_CSRF_TRUSTED_ORIGINS` - Your HTTPS URLs

### 2. Set Up SSL Certificates

**Using Let's Encrypt (Recommended):**

```bash
# Install certbot
sudo apt install certbot

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
```

**Using Self-Signed (Development Only):**

```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=yourdomain.com"
```

### 3. Deploy Services

```bash
# Deploy with monitoring stack
docker-compose -f docker-compose.prod.enhanced.yml up -d

# Check all services are running
docker-compose -f docker-compose.prod.enhanced.yml ps
```

### 4. Initialize Database

```bash
# Run migrations
docker-compose -f docker-compose.prod.enhanced.yml exec web python manage.py migrate

# Create superuser
docker-compose -f docker-compose.prod.enhanced.yml exec web python manage.py createsuperuser

# Collect static files
docker-compose -f docker-compose.prod.enhanced.yml exec web python manage.py collectstatic --noinput

# Optional: Load demo data
docker-compose -f docker-compose.prod.enhanced.yml exec web python manage.py generate_demo_data --days 30
```

### 5. Set Up Automated Backups

```bash
# Make backup scripts executable
chmod +x scripts/backup/backup-database.sh
chmod +x scripts/backup/backup-media.sh

# Add to crontab
crontab -e

# Add these lines:
0 2 * * * /path/to/datadestroyer/scripts/backup/backup-database.sh >> /var/log/destroyer-backup.log 2>&1
0 3 * * 0 /path/to/datadestroyer/scripts/backup/backup-media.sh >> /var/log/destroyer-backup.log 2>&1
```

## Post-Deployment Tasks

### 1. Security Hardening

```bash
# Configure firewall
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# Verify environment file permissions
chmod 600 .env.production
```

### 2. SSL Auto-Renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Auto-renewal is typically configured by default with certbot
# Verify with:
sudo systemctl status certbot.timer
```

### 3. Configure Monitoring Alerts

Edit `monitoring/prometheus/alerts.yml` to set up alerts for:
- High error rates
- Service downtime
- High resource usage
- Failed health checks

### 4. Test Critical Workflows

Verify these workflows work correctly:
- ✅ User registration and login
- ✅ Data discovery scans
- ✅ ML classification
- ✅ Policy creation
- ✅ Compliance reports
- ✅ Active learning feedback

## Common Operations

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.enhanced.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.enhanced.yml logs -f web
docker-compose -f docker-compose.prod.enhanced.yml logs -f celery-worker

# Last 100 lines
docker-compose -f docker-compose.prod.enhanced.yml logs --tail=100 web
```

### Restart Services

```bash
# Restart specific service
docker-compose -f docker-compose.prod.enhanced.yml restart web

# Restart all services
docker-compose -f docker-compose.prod.enhanced.yml restart

# Zero-downtime restart
docker-compose -f docker-compose.prod.enhanced.yml up -d --no-deps --scale web=2 web
docker-compose -f docker-compose.prod.enhanced.yml up -d --no-deps --scale web=1 web
```

### Database Operations

```bash
# Run migrations
docker-compose -f docker-compose.prod.enhanced.yml exec web python manage.py migrate

# Create database backup
./scripts/backup/backup-database.sh

# Restore from backup
gunzip -c /backups/postgres/destroyer_db_TIMESTAMP.sql.gz | \
  docker-compose -f docker-compose.prod.enhanced.yml exec -T db psql -U destroyer -d postgres

# Access database shell
docker-compose -f docker-compose.prod.enhanced.yml exec db psql -U destroyer -d destroyer
```

### Update Deployment

```bash
# Pull latest code
git pull origin main

# Rebuild images
docker-compose -f docker-compose.prod.enhanced.yml build

# Deploy updates
docker-compose -f docker-compose.prod.enhanced.yml up -d

# Run any new migrations
docker-compose -f docker-compose.prod.enhanced.yml exec web python manage.py migrate
```

### Train ML Models

```bash
# Train model with user feedback
docker-compose -f docker-compose.prod.enhanced.yml exec web \
  python manage.py train_ml_model --iterations 30

# With custom parameters
docker-compose -f docker-compose.prod.enhanced.yml exec web \
  python manage.py train_ml_model \
  --model en_core_web_trf \
  --iterations 50 \
  --test-split 0.3 \
  --min-samples 20
```

## Monitoring and Maintenance

### Daily Checks

- ✅ Check Grafana dashboards for anomalies
- ✅ Review error rates in Prometheus
- ✅ Verify automated backups completed
- ✅ Check disk space and resource usage

### Weekly Maintenance

- ✅ Review application logs
- ✅ Check for security updates
- ✅ Test backup restoration
- ✅ Review ML model performance metrics

### Monthly Maintenance

- ✅ Update Docker images
- ✅ Review and optimize database queries
- ✅ Analyze user feedback for ML improvements
- ✅ Review and update documentation

## Troubleshooting

### Services Won't Start

```bash
# Check logs for errors
docker-compose -f docker-compose.prod.enhanced.yml logs web

# Verify environment variables
cat .env.production

# Rebuild images
docker-compose -f docker-compose.prod.enhanced.yml build --no-cache
docker-compose -f docker-compose.prod.enhanced.yml up -d
```

### Health Checks Failing

```bash
# Test health endpoint directly
docker-compose -f docker-compose.prod.enhanced.yml exec web curl http://localhost:8000/health/

# Check database connectivity
docker-compose -f docker-compose.prod.enhanced.yml exec db pg_isready -U destroyer

# Check Redis
docker-compose -f docker-compose.prod.enhanced.yml exec redis redis-cli ping
```

### High Memory Usage

```bash
# Check resource usage
docker stats

# Restart Celery workers to clear memory
docker-compose -f docker-compose.prod.enhanced.yml restart celery-worker celery-beat

# Adjust worker count in .env.production
CELERY_WORKERS=2  # Reduce from 4 if memory constrained
```

### SSL Certificate Issues

```bash
# Check certificate expiry
openssl x509 -in nginx/ssl/cert.pem -noout -enddate

# Renew Let's Encrypt certificate
sudo certbot renew

# Copy renewed certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem

# Restart Nginx
docker-compose -f docker-compose.prod.enhanced.yml restart nginx
```

## Performance Optimization

### Database Optimization

```bash
# Run database vacuum (reduces bloat)
docker-compose -f docker-compose.prod.enhanced.yml exec db \
  psql -U destroyer -d destroyer -c "VACUUM ANALYZE;"

# Check slow queries
docker-compose -f docker-compose.prod.enhanced.yml exec db \
  psql -U destroyer -d destroyer -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

### Cache Optimization

```bash
# Check Redis memory usage
docker-compose -f docker-compose.prod.enhanced.yml exec redis redis-cli INFO memory

# Clear cache if needed
docker-compose -f docker-compose.prod.enhanced.yml exec web python manage.py clear_cache
```

### Scale Services

```bash
# Scale web workers
docker-compose -f docker-compose.prod.enhanced.yml up -d --scale web=3

# Scale Celery workers
docker-compose -f docker-compose.prod.enhanced.yml up -d --scale celery-worker=6
```

## CI/CD Integration

The platform includes automated CI/CD via GitHub Actions.

### Required GitHub Secrets

Configure in **Settings → Secrets and variables → Actions**:

```
DEPLOY_SSH_KEY         # SSH private key for production server
DEPLOY_HOST            # Production server hostname/IP
DEPLOY_USER            # SSH username
GRAFANA_ADMIN_PASSWORD # Grafana password
```

### Deployment Workflow

```bash
# Automatic deployment on push to main
git push origin main

# Manual deployment with tag
git tag v1.0.0
git push origin v1.0.0
```

The CI/CD pipeline will:
1. Run all tests (backend + frontend)
2. Perform security scanning
3. Build Docker images
4. Push to GitHub Container Registry
5. Deploy to production server
6. Run health checks

## Support and Resources

### Documentation

- **Full Deployment Guide**: [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)
- **Production Hardening**: [PRODUCTION_HARDENING_COMPLETE.md](PRODUCTION_HARDENING_COMPLETE.md)
- **ML Classification**: [ML_CLASSIFICATION_COMPLETE.md](ML_CLASSIFICATION_COMPLETE.md)
- **Active Learning**: [ACTIVE_LEARNING_COMPLETE.md](ACTIVE_LEARNING_COMPLETE.md)

### Useful Commands Reference

```bash
# Deployment
./scripts/deploy/deploy-production.sh          # Automated deployment
./scripts/deploy/verify-deployment.sh          # Verify deployment

# Backups
./scripts/backup/backup-database.sh            # Manual database backup
./scripts/backup/backup-media.sh               # Manual media backup

# Monitoring
docker-compose logs -f                         # View all logs
docker stats                                   # Resource usage
docker-compose ps                              # Service status

# Maintenance
docker system prune -a                         # Clean up Docker
docker volume prune                            # Clean up volumes
docker-compose restart                         # Restart all services
```

### Health Check Endpoints

- `https://yourdomain.com/health/` - Comprehensive health check
- `https://yourdomain.com/ready/` - Kubernetes readiness probe
- `https://yourdomain.com/alive/` - Kubernetes liveness probe
- `https://yourdomain.com/api/metrics/` - Application metrics

### Performance Targets

- **Uptime**: 99.9%
- **Response Time**: < 500ms average
- **Database Query**: < 2s
- **Cache Hit Rate**: 95%+
- **SSL Rating**: A+

## Production Checklist

Before going live, verify:

- [ ] SSL/TLS certificates configured (A+ rating on SSL Labs)
- [ ] All health checks passing (`./scripts/deploy/verify-deployment.sh`)
- [ ] Automated backups configured and tested
- [ ] Monitoring dashboards set up in Grafana
- [ ] CI/CD pipeline configured and tested
- [ ] Firewall rules configured (only 22, 80, 443 open)
- [ ] `.env.production` secured (permissions 600, not in git)
- [ ] All database migrations applied
- [ ] Static files serving correctly
- [ ] Sentry error tracking configured (optional)
- [ ] Load testing completed
- [ ] Disaster recovery plan documented and tested
- [ ] DNS configured correctly
- [ ] Superuser account created
- [ ] Critical workflows tested end-to-end

---

**Version**: 1.0.0
**Status**: Production Ready ✅
**Last Updated**: 2025-11-08

For issues or questions, see the full documentation or contact support.
