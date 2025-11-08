#!/bin/bash

# ============================================================================
# Data Destroyer - Production Deployment Script
# ============================================================================
# This script automates the deployment of Data Destroyer to production
# Usage: ./scripts/deploy/deploy-production.sh
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed. Please install it first."
        exit 1
    fi
}

# ============================================================================
# Pre-deployment Checks
# ============================================================================

echo "============================================================================"
echo "Data Destroyer - Production Deployment"
echo "============================================================================"
echo ""

log_info "Running pre-deployment checks..."

# Check required commands
check_command docker
check_command docker-compose
check_command git

# Check Docker daemon
if ! docker info &> /dev/null; then
    log_error "Docker daemon is not running. Please start Docker."
    exit 1
fi

log_success "All required tools are installed"

# ============================================================================
# Environment Configuration
# ============================================================================

log_info "Checking environment configuration..."

cd "$PROJECT_ROOT"

if [ ! -f .env.production ]; then
    log_warning ".env.production not found. Creating from template..."
    cp .env.production.example .env.production
    log_warning "Please edit .env.production with your production values!"
    log_warning "Required: DJANGO_SECRET_KEY, POSTGRES_PASSWORD, GRAFANA_ADMIN_PASSWORD, DJANGO_ALLOWED_HOSTS"
    echo ""
    read -p "Press Enter after you've configured .env.production..."
fi

# Verify critical environment variables
source .env.production

if [ "$DJANGO_SECRET_KEY" == "REPLACE_WITH_A_LONG_RANDOM_SECRET_KEY_MIN_50_CHARS" ]; then
    log_error "DJANGO_SECRET_KEY not configured in .env.production"
    log_info "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(50))\""
    exit 1
fi

if [ "$POSTGRES_PASSWORD" == "REPLACE_WITH_SECURE_PASSWORD" ]; then
    log_error "POSTGRES_PASSWORD not configured in .env.production"
    exit 1
fi

log_success "Environment configuration verified"

# ============================================================================
# SSL Certificate Check
# ============================================================================

log_info "Checking SSL certificates..."

if [ ! -d nginx/ssl ]; then
    mkdir -p nginx/ssl
fi

if [ ! -f nginx/ssl/cert.pem ] || [ ! -f nginx/ssl/key.pem ]; then
    log_warning "SSL certificates not found in nginx/ssl/"
    echo ""
    echo "Choose SSL certificate option:"
    echo "1) Use Let's Encrypt (recommended for production)"
    echo "2) Generate self-signed certificate (development only)"
    echo "3) I'll copy my certificates manually"
    echo ""
    read -p "Enter choice [1-3]: " ssl_choice

    case $ssl_choice in
        1)
            log_info "Let's Encrypt setup requires certbot"
            read -p "Enter your domain name: " domain
            log_info "Run: sudo certbot certonly --standalone -d $domain"
            log_info "Then copy certificates:"
            log_info "  sudo cp /etc/letsencrypt/live/$domain/fullchain.pem nginx/ssl/cert.pem"
            log_info "  sudo cp /etc/letsencrypt/live/$domain/privkey.pem nginx/ssl/key.pem"
            exit 0
            ;;
        2)
            log_warning "Generating self-signed certificate..."
            openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                -keyout nginx/ssl/key.pem \
                -out nginx/ssl/cert.pem \
                -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
            log_success "Self-signed certificate created"
            ;;
        3)
            log_info "Please copy your SSL certificates to nginx/ssl/"
            log_info "  nginx/ssl/cert.pem (certificate)"
            log_info "  nginx/ssl/key.pem (private key)"
            read -p "Press Enter after copying certificates..."
            ;;
    esac
fi

if [ -f nginx/ssl/cert.pem ] && [ -f nginx/ssl/key.pem ]; then
    log_success "SSL certificates found"
else
    log_error "SSL certificates not configured"
    exit 1
fi

# ============================================================================
# Pull Latest Code
# ============================================================================

log_info "Pulling latest code..."

# Show current branch
current_branch=$(git branch --show-current)
log_info "Current branch: $current_branch"

# Ask if user wants to pull/merge
if [ "$current_branch" != "main" ] && [ "$current_branch" != "master" ]; then
    log_warning "Not on main/master branch"
    read -p "Do you want to merge this branch to main? (y/n): " merge_choice
    if [ "$merge_choice" == "y" ]; then
        log_info "Switching to main branch..."
        git checkout main 2>/dev/null || git checkout -b main
        log_info "Merging $current_branch into main..."
        git merge "$current_branch" --no-edit
        log_success "Branch merged to main"
    fi
fi

# ============================================================================
# Docker Image Build/Pull
# ============================================================================

log_info "Preparing Docker images..."

# Check if we should build or pull
read -p "Build Docker images locally or pull from registry? (build/pull): " image_choice

if [ "$image_choice" == "build" ]; then
    log_info "Building Docker images..."
    docker-compose -f docker-compose.prod.enhanced.yml build --no-cache
    log_success "Docker images built successfully"
else
    log_info "Pulling Docker images from registry..."
    docker-compose -f docker-compose.prod.enhanced.yml pull || {
        log_warning "Failed to pull images. Building locally instead..."
        docker-compose -f docker-compose.prod.enhanced.yml build
    }
fi

# ============================================================================
# Deploy Services
# ============================================================================

log_info "Deploying services..."

# Stop existing containers
if docker-compose -f docker-compose.prod.enhanced.yml ps | grep -q "Up"; then
    log_info "Stopping existing containers..."
    docker-compose -f docker-compose.prod.enhanced.yml down
fi

# Start services
log_info "Starting all services..."
docker-compose -f docker-compose.prod.enhanced.yml up -d

# Wait for services to be healthy
log_info "Waiting for services to be healthy (this may take up to 60 seconds)..."
sleep 10

# Check database is ready
log_info "Waiting for database..."
for i in {1..30}; do
    if docker-compose -f docker-compose.prod.enhanced.yml exec -T db pg_isready -U destroyer &> /dev/null; then
        log_success "Database is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        log_error "Database failed to start"
        exit 1
    fi
    sleep 2
done

# ============================================================================
# Database Initialization
# ============================================================================

log_info "Running database migrations..."
docker-compose -f docker-compose.prod.enhanced.yml exec -T web python manage.py migrate --noinput

log_info "Collecting static files..."
docker-compose -f docker-compose.prod.enhanced.yml exec -T web python manage.py collectstatic --noinput --clear

# Check if superuser exists
log_info "Checking for superuser..."
superuser_exists=$(docker-compose -f docker-compose.prod.enhanced.yml exec -T web python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print(User.objects.filter(is_superuser=True).exists())" 2>/dev/null || echo "False")

if [[ "$superuser_exists" == *"False"* ]]; then
    log_warning "No superuser found. Creating one..."
    read -p "Do you want to create a superuser now? (y/n): " create_superuser
    if [ "$create_superuser" == "y" ]; then
        docker-compose -f docker-compose.prod.enhanced.yml exec web python manage.py createsuperuser
    else
        log_info "You can create a superuser later with:"
        log_info "  docker-compose -f docker-compose.prod.enhanced.yml exec web python manage.py createsuperuser"
    fi
fi

# ============================================================================
# Load Demo Data (Optional)
# ============================================================================

read -p "Do you want to load demo data? (y/n): " load_demo
if [ "$load_demo" == "y" ]; then
    log_info "Loading demo data..."
    docker-compose -f docker-compose.prod.enhanced.yml exec -T web python manage.py generate_demo_data --days 30
    log_success "Demo data loaded"
fi

# ============================================================================
# Verify Deployment
# ============================================================================

log_info "Verifying deployment..."

# Check all services are running
log_info "Checking service status..."
docker-compose -f docker-compose.prod.enhanced.yml ps

# Test health endpoint
log_info "Testing health endpoint..."
sleep 5  # Give services a moment to fully start

health_check=$(docker-compose -f docker-compose.prod.enhanced.yml exec -T web curl -s http://localhost:8000/health/ 2>/dev/null || echo '{"status":"error"}')
if echo "$health_check" | grep -q '"status":"healthy"'; then
    log_success "Health check passed"
else
    log_warning "Health check failed or returned degraded status"
    echo "$health_check"
fi

# ============================================================================
# Setup Automated Backups
# ============================================================================

log_info "Setting up automated backups..."

# Make backup scripts executable
chmod +x scripts/backup/backup-database.sh
chmod +x scripts/backup/backup-media.sh

read -p "Do you want to set up automated backups via cron? (y/n): " setup_cron
if [ "$setup_cron" == "y" ]; then
    log_info "Adding cron jobs..."

    # Check if cron jobs already exist
    if crontab -l 2>/dev/null | grep -q "backup-database.sh"; then
        log_info "Backup cron jobs already configured"
    else
        # Add to crontab
        (crontab -l 2>/dev/null; echo "# Data Destroyer - Daily database backup at 2 AM") | crontab -
        (crontab -l 2>/dev/null; echo "0 2 * * * $PROJECT_ROOT/scripts/backup/backup-database.sh >> /var/log/destroyer-backup.log 2>&1") | crontab -
        (crontab -l 2>/dev/null; echo "# Data Destroyer - Weekly media backup on Sunday at 3 AM") | crontab -
        (crontab -l 2>/dev/null; echo "0 3 * * 0 $PROJECT_ROOT/scripts/backup/backup-media.sh >> /var/log/destroyer-backup.log 2>&1") | crontab -
        log_success "Cron jobs added"
    fi

    log_info "Backup schedule:"
    log_info "  Database: Daily at 2:00 AM"
    log_info "  Media: Weekly on Sunday at 3:00 AM"
fi

# ============================================================================
# Deployment Summary
# ============================================================================

echo ""
echo "============================================================================"
log_success "Deployment completed successfully!"
echo "============================================================================"
echo ""

echo "Access Points:"
echo "  Application: https://$(echo $DJANGO_ALLOWED_HOSTS | cut -d',' -f1)"
echo "  Admin Panel: https://$(echo $DJANGO_ALLOWED_HOSTS | cut -d',' -f1)/admin/"
echo "  API Docs: https://$(echo $DJANGO_ALLOWED_HOSTS | cut -d',' -f1)/api/docs/"
echo "  Grafana: http://$(hostname):3000 (user: admin, password from .env)"
echo "  Prometheus: http://$(hostname):9090"
echo ""

echo "Health Check Endpoints:"
echo "  Health: https://$(echo $DJANGO_ALLOWED_HOSTS | cut -d',' -f1)/health/"
echo "  Ready: https://$(echo $DJANGO_ALLOWED_HOSTS | cut -d',' -f1)/ready/"
echo "  Metrics: https://$(echo $DJANGO_ALLOWED_HOSTS | cut -d',' -f1)/api/metrics/"
echo ""

echo "Useful Commands:"
echo "  View logs: docker-compose -f docker-compose.prod.enhanced.yml logs -f"
echo "  Check status: docker-compose -f docker-compose.prod.enhanced.yml ps"
echo "  Restart services: docker-compose -f docker-compose.prod.enhanced.yml restart"
echo "  Stop services: docker-compose -f docker-compose.prod.enhanced.yml down"
echo "  Manual backup: ./scripts/backup/backup-database.sh"
echo ""

echo "Next Steps:"
echo "  1. Configure Grafana dashboards (import IDs: 9528, 9628, 763, 1860)"
echo "  2. Set up SSL auto-renewal (certbot renew)"
echo "  3. Configure monitoring alerts"
echo "  4. Review and customize .env.production settings"
echo "  5. Test all critical workflows"
echo ""

log_info "For detailed documentation, see PRODUCTION_DEPLOYMENT.md"

echo "============================================================================"
