#!/bin/bash

# ============================================================================
# Data Destroyer - Deployment Verification Script
# ============================================================================
# This script verifies the production deployment is working correctly
# Usage: ./scripts/deploy/verify-deployment.sh
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}[✗]${NC} $1"
    ((FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
    ((WARNINGS++))
}

check_service() {
    local service=$1
    local description=$2

    if docker-compose -f docker-compose.prod.enhanced.yml ps | grep "$service" | grep -q "Up"; then
        log_pass "$description is running"
        return 0
    else
        log_fail "$description is not running"
        return 1
    fi
}

check_http_endpoint() {
    local url=$1
    local description=$2
    local expected_status=${3:-200}

    status=$(curl -k -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")

    if [ "$status" == "$expected_status" ]; then
        log_pass "$description (HTTP $status)"
        return 0
    else
        log_fail "$description (HTTP $status, expected $expected_status)"
        return 1
    fi
}

check_health_endpoint() {
    local url=$1
    local description=$2

    response=$(curl -k -s "$url" 2>/dev/null || echo '{"status":"error"}')
    status=$(echo "$response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

    if [ "$status" == "healthy" ] || [ "$status" == "ready" ] || [ "$status" == "alive" ]; then
        log_pass "$description (status: $status)"
        return 0
    else
        log_fail "$description (status: $status)"
        return 1
    fi
}

# ============================================================================
# Start Verification
# ============================================================================

echo "============================================================================"
echo "Data Destroyer - Deployment Verification"
echo "============================================================================"
echo ""

# Load environment
if [ -f .env.production ]; then
    source .env.production
else
    log_fail ".env.production not found"
    exit 1
fi

# Extract first domain from ALLOWED_HOSTS
DOMAIN=$(echo "$DJANGO_ALLOWED_HOSTS" | cut -d',' -f1)
BASE_URL="http://localhost:8000"  # Internal check
EXTERNAL_URL="https://$DOMAIN"     # External check

# ============================================================================
# Docker Services Check
# ============================================================================

log_info "Checking Docker services..."
echo ""

check_service "db" "PostgreSQL Database"
check_service "redis" "Redis Cache"
check_service "web" "Django Backend"
check_service "celery-worker" "Celery Worker"
check_service "celery-beat" "Celery Beat"
check_service "nginx" "Nginx Reverse Proxy"
check_service "prometheus" "Prometheus Metrics"
check_service "grafana" "Grafana Dashboards"

echo ""

# ============================================================================
# Database Check
# ============================================================================

log_info "Checking database connectivity..."
echo ""

if docker-compose -f docker-compose.prod.enhanced.yml exec -T db pg_isready -U "$POSTGRES_USER" &> /dev/null; then
    log_pass "Database is accepting connections"
else
    log_fail "Database is not ready"
fi

# Check migrations
migration_check=$(docker-compose -f docker-compose.prod.enhanced.yml exec -T web python manage.py showmigrations 2>&1 | grep -c "\[ \]" || echo "0")
if [ "$migration_check" == "0" ]; then
    log_pass "All database migrations applied"
else
    log_warning "$migration_check unapplied migrations found"
fi

echo ""

# ============================================================================
# Health Endpoints Check
# ============================================================================

log_info "Checking health endpoints..."
echo ""

# Internal health checks (direct to Django)
if command -v docker-compose &> /dev/null; then
    # Check from inside container
    health_response=$(docker-compose -f docker-compose.prod.enhanced.yml exec -T web curl -s http://localhost:8000/health/ 2>/dev/null || echo '{"status":"error"}')
    health_status=$(echo "$health_response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

    if [ "$health_status" == "healthy" ]; then
        log_pass "Django health check"
    else
        log_fail "Django health check (status: $health_status)"
    fi

    # Readiness check
    ready_response=$(docker-compose -f docker-compose.prod.enhanced.yml exec -T web curl -s http://localhost:8000/ready/ 2>/dev/null || echo '{"status":"error"}')
    ready_status=$(echo "$ready_response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

    if [ "$ready_status" == "ready" ]; then
        log_pass "Readiness probe"
    else
        log_fail "Readiness probe (status: $ready_status)"
    fi

    # Liveness check
    alive_response=$(docker-compose -f docker-compose.prod.enhanced.yml exec -T web curl -s http://localhost:8000/alive/ 2>/dev/null || echo '{"status":"error"}')
    alive_status=$(echo "$alive_response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

    if [ "$alive_status" == "alive" ]; then
        log_pass "Liveness probe"
    else
        log_fail "Liveness probe (status: $alive_status)"
    fi
fi

echo ""

# ============================================================================
# API Endpoints Check
# ============================================================================

log_info "Checking API endpoints..."
echo ""

# Check if we can reach endpoints via Nginx
if curl -k -s "https://$DOMAIN/health/" &> /dev/null; then
    check_http_endpoint "https://$DOMAIN/health/" "External health endpoint (via Nginx)"
    check_http_endpoint "https://$DOMAIN/api/metrics/" "Metrics endpoint"
else
    log_warning "External endpoints not accessible (check Nginx/firewall/DNS)"
fi

# Check admin is accessible
check_http_endpoint "http://localhost:8000/admin/" "Admin panel" 302

echo ""

# ============================================================================
# Static Files Check
# ============================================================================

log_info "Checking static files..."
echo ""

static_check=$(docker-compose -f docker-compose.prod.enhanced.yml exec -T web ls staticfiles/ 2>/dev/null | wc -l)
if [ "$static_check" -gt 0 ]; then
    log_pass "Static files collected ($static_check files/dirs found)"
else
    log_fail "No static files found"
fi

echo ""

# ============================================================================
# Monitoring Stack Check
# ============================================================================

log_info "Checking monitoring stack..."
echo ""

# Prometheus
if curl -s http://localhost:9090/-/healthy &> /dev/null; then
    log_pass "Prometheus is healthy"
else
    log_warning "Prometheus health check failed"
fi

# Grafana
if curl -s http://localhost:3000/api/health &> /dev/null; then
    log_pass "Grafana is healthy"
else
    log_warning "Grafana health check failed"
fi

# Check Prometheus targets
targets_up=$(curl -s http://localhost:9090/api/v1/targets 2>/dev/null | grep -o '"health":"up"' | wc -l)
if [ "$targets_up" -gt 0 ]; then
    log_pass "Prometheus has $targets_up targets up"
else
    log_warning "No Prometheus targets are up"
fi

echo ""

# ============================================================================
# SSL Certificate Check
# ============================================================================

log_info "Checking SSL certificates..."
echo ""

if [ -f nginx/ssl/cert.pem ] && [ -f nginx/ssl/key.pem ]; then
    log_pass "SSL certificate files exist"

    # Check certificate expiry
    cert_expiry=$(openssl x509 -in nginx/ssl/cert.pem -noout -enddate 2>/dev/null | cut -d'=' -f2)
    if [ -n "$cert_expiry" ]; then
        log_info "Certificate expires: $cert_expiry"

        # Check if expires in less than 30 days
        expiry_epoch=$(date -d "$cert_expiry" +%s 2>/dev/null || echo "0")
        now_epoch=$(date +%s)
        days_until_expiry=$(( ($expiry_epoch - $now_epoch) / 86400 ))

        if [ "$days_until_expiry" -lt 30 ] && [ "$days_until_expiry" -gt 0 ]; then
            log_warning "Certificate expires in $days_until_expiry days - renew soon!"
        elif [ "$days_until_expiry" -le 0 ]; then
            log_fail "Certificate has expired!"
        else
            log_pass "Certificate valid for $days_until_expiry days"
        fi
    fi
else
    log_fail "SSL certificate files not found"
fi

echo ""

# ============================================================================
# Backup Configuration Check
# ============================================================================

log_info "Checking backup configuration..."
echo ""

if [ -f scripts/backup/backup-database.sh ] && [ -x scripts/backup/backup-database.sh ]; then
    log_pass "Database backup script is executable"
else
    log_warning "Database backup script not found or not executable"
fi

if [ -f scripts/backup/backup-media.sh ] && [ -x scripts/backup/backup-media.sh ]; then
    log_pass "Media backup script is executable"
else
    log_warning "Media backup script not found or not executable"
fi

# Check cron jobs
if crontab -l 2>/dev/null | grep -q "backup-database.sh"; then
    log_pass "Automated database backups configured"
else
    log_warning "Automated database backups not configured"
fi

# Check backup directory
if [ -d "$BACKUP_DIR" ]; then
    backup_count=$(find "$BACKUP_DIR" -name "*.sql.gz" 2>/dev/null | wc -l)
    if [ "$backup_count" -gt 0 ]; then
        log_pass "Found $backup_count database backup(s)"
    else
        log_warning "No database backups found in $BACKUP_DIR"
    fi
else
    log_warning "Backup directory $BACKUP_DIR does not exist"
fi

echo ""

# ============================================================================
# Environment Variables Check
# ============================================================================

log_info "Checking critical environment variables..."
echo ""

if [ "$DEBUG" == "False" ] || [ "$DEBUG" == "false" ]; then
    log_pass "DEBUG mode is disabled"
else
    log_fail "DEBUG mode is enabled (security risk!)"
fi

if [ -n "$DJANGO_SECRET_KEY" ] && [ "$DJANGO_SECRET_KEY" != "REPLACE_WITH_A_LONG_RANDOM_SECRET_KEY_MIN_50_CHARS" ]; then
    log_pass "DJANGO_SECRET_KEY is configured"
else
    log_fail "DJANGO_SECRET_KEY not properly configured"
fi

if [ -n "$DJANGO_ALLOWED_HOSTS" ]; then
    log_pass "DJANGO_ALLOWED_HOSTS is configured"
else
    log_fail "DJANGO_ALLOWED_HOSTS not configured"
fi

if [ "$SECURE_SSL_REDIRECT" == "True" ] || [ "$SECURE_SSL_REDIRECT" == "true" ]; then
    log_pass "SSL redirect is enabled"
else
    log_warning "SSL redirect is not enabled"
fi

echo ""

# ============================================================================
# Resource Usage Check
# ============================================================================

log_info "Checking resource usage..."
echo ""

# Memory usage
total_mem=$(free -m | awk 'NR==2{print $2}')
used_mem=$(free -m | awk 'NR==2{print $3}')
mem_percent=$(( used_mem * 100 / total_mem ))

if [ "$mem_percent" -lt 80 ]; then
    log_pass "Memory usage: ${mem_percent}% (${used_mem}MB / ${total_mem}MB)"
elif [ "$mem_percent" -lt 90 ]; then
    log_warning "Memory usage: ${mem_percent}% (${used_mem}MB / ${total_mem}MB)"
else
    log_fail "Memory usage critical: ${mem_percent}% (${used_mem}MB / ${total_mem}MB)"
fi

# Disk usage
disk_usage=$(df -h / | awk 'NR==2{print $5}' | sed 's/%//')
if [ "$disk_usage" -lt 80 ]; then
    log_pass "Disk usage: ${disk_usage}%"
elif [ "$disk_usage" -lt 90 ]; then
    log_warning "Disk usage: ${disk_usage}%"
else
    log_fail "Disk usage critical: ${disk_usage}%"
fi

# Docker disk usage
docker_df=$(docker system df --format "{{.Type}}\t{{.Size}}" 2>/dev/null || echo "")
if [ -n "$docker_df" ]; then
    log_info "Docker disk usage:"
    echo "$docker_df" | while read -r line; do
        echo "    $line"
    done
fi

echo ""

# ============================================================================
# Log Check
# ============================================================================

log_info "Checking for recent errors in logs..."
echo ""

error_count=$(docker-compose -f docker-compose.prod.enhanced.yml logs --tail=100 web 2>/dev/null | grep -i "error" | wc -l)
if [ "$error_count" -eq 0 ]; then
    log_pass "No errors in recent logs"
elif [ "$error_count" -lt 5 ]; then
    log_warning "$error_count error(s) found in recent logs"
else
    log_fail "$error_count error(s) found in recent logs"
fi

warning_count=$(docker-compose -f docker-compose.prod.enhanced.yml logs --tail=100 web 2>/dev/null | grep -i "warning" | wc -l)
if [ "$warning_count" -lt 5 ]; then
    log_pass "$warning_count warning(s) in recent logs"
else
    log_warning "$warning_count warning(s) in recent logs"
fi

echo ""

# ============================================================================
# Summary
# ============================================================================

echo "============================================================================"
echo "Verification Summary"
echo "============================================================================"
echo ""

total_checks=$((PASSED + FAILED + WARNINGS))
echo "Total Checks: $total_checks"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ Deployment is fully operational!${NC}"
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}⚠ Deployment is operational with warnings${NC}"
    echo "Review warnings above and address if necessary."
    exit 0
else
    echo -e "${RED}✗ Deployment has critical issues${NC}"
    echo "Fix failed checks before going to production."
    exit 1
fi
