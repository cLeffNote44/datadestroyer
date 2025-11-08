# Data Destroyer

<div align="center">

**Enterprise-grade data privacy and governance platform for any company that is serious about what they do**

**This software could fit perfectly in many industries:**

- **Healthcare**
- **Financial Services**
- **Tech and SaaS Companies**
- **Insurance**
- **Legal**
- **HR**
- **Recruitment** 
- **Education**
- **Government**

**Any segment that needs oversight, securitty, or that just deals with Compliance.** 

**This was a fun one to build! email us with feedback! cLeffNote@pm.me**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Django 4.2+](https://img.shields.io/badge/django-4.2+-green.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)

</div>

## Overview

Data Destroyer is a comprehensive data privacy and governance platform designed to help organizations discover, classify, and manage sensitive data across their infrastructure. Built with Django and powered by machine learning, it provides automated PII/PHI/PCI detection, policy enforcement, and compliance reporting.

### Key Features

- **🔍 AI-Powered Data Discovery** - Hybrid ML engine combining regex patterns and spaCy NER for accurate sensitive data detection
- **🧠 Active Learning** - Continuously improves classification accuracy through user feedback and model retraining
- **📊 Real-time Monitoring** - Prometheus metrics and Grafana dashboards for comprehensive observability
- **🔒 Policy Enforcement** - Flexible policy engine with automated violation detection and remediation workflows
- **📈 Compliance Reporting** - Pre-built templates for GDPR, HIPAA, PCI-DSS, and custom compliance frameworks
- **🚀 Production-Ready** - Docker orchestration, automated backups, CI/CD pipelines, and health checks
- **🔐 Enterprise Security** - SSL/TLS, rate limiting, RBAC, and comprehensive audit logging

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Nginx (Reverse Proxy)                  │
│                     SSL/TLS + Rate Limiting                 │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼─────┐    ┌────▼─────┐    ┌────▼─────┐
   │  Django  │    │  Celery  │    │  Celery  │
   │ Backend  │    │  Worker  │    │   Beat   │
   └────┬─────┘    └────┬─────┘    └────┬─────┘
        │               │                │
        └───────┬───────┴───────┬────────┘
                │               │
        ┌───────▼──────┐  ┌────▼──────┐
        │  PostgreSQL  │  │   Redis   │
        │  (Database)  │  │  (Cache)  │
        └──────────────┘  └───────────┘

Monitoring:  Prometheus → Grafana
ML Engine:   Regex + spaCy NER → Active Learning
```

## Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- 40GB disk space

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/datadestroyer.git
cd datadestroyer
```

2. **Configure environment**

```bash
cp .env.production.example .env.production
# Edit .env.production with your values
nano .env.production
```

Required environment variables:
- `DJANGO_SECRET_KEY` - Generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"`
- `POSTGRES_PASSWORD` - Database password
- `DJANGO_ALLOWED_HOSTS` - Your domain(s)

3. **Deploy with Docker**

```bash
# Production deployment (automated)
./scripts/deploy/deploy-production.sh

# Or manually
docker-compose -f docker-compose.prod.enhanced.yml up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

4. **Verify deployment**

```bash
./scripts/deploy/verify-deployment.sh
```

5. **Access the platform**

- Application: `https://yourdomain.com`
- Admin: `https://yourdomain.com/admin/`
- API Docs: `https://yourdomain.com/api/docs/`
- Grafana: `http://yourserver:3000`

## ML Classification Engine

The platform uses a hybrid machine learning approach for sensitive data classification:

### Supported Data Types

- **PII**: Names, emails, phone numbers, addresses, SSN, credit cards
- **PHI**: Medical record numbers, health insurance IDs, diagnosis codes
- **PCI**: Credit card numbers, CVV, account numbers
- **Custom**: Configurable patterns for organization-specific data

### API Usage

```python
# Classify text
POST /api/discovery/ml/classify/
{
  "text": "Contact John Smith at john.smith@example.com or call 555-123-4567"
}

# Response
{
  "entities": [
    {"text": "John Smith", "label": "PERSON", "confidence": 0.95},
    {"text": "john.smith@example.com", "label": "EMAIL", "confidence": 1.0},
    {"text": "555-123-4567", "label": "PHONE", "confidence": 0.98}
  ],
  "confidence_score": 0.98
}
```

### Active Learning

Submit feedback to improve model accuracy:

```python
POST /api/discovery/ml/feedback/
{
  "text": "Sample text...",
  "is_correct": false,
  "corrected_entities": [...]
}
```

Train models with accumulated feedback:

```bash
docker-compose exec web python manage.py train_ml_model --iterations 30
```

## Development

### Local Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements/dev.txt

# Run development server
python manage.py migrate
python manage.py runserver
```

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=. --cov-report=html

# Specific test file
pytest discovery/tests/test_ml_classification.py
```

### Code Quality

```bash
# Format code
black .
isort .

# Linting
ruff check .
mypy .

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

## Deployment

### Production Deployment

See [Quick Start Guide](docs/deployment/quick-start.md) for automated deployment.

For detailed production configuration:
- [Production Deployment Guide](docs/deployment/production.md)
- [ML Architecture Documentation](docs/architecture/ml-classification.md)

### CI/CD

GitHub Actions workflow automatically:
1. Runs tests on every push/PR
2. Performs security scans
3. Builds and pushes Docker images
4. Deploys to production (on main branch)

### Monitoring

Access monitoring dashboards:
- **Grafana**: Pre-configured dashboards for Django, PostgreSQL, Redis, and system metrics
- **Prometheus**: Metrics collection with 30-day retention
- **Health Checks**: `/health/`, `/ready/`, `/alive/` endpoints

### Backups

Automated backups:
- **Database**: Daily at 2 AM (30-day retention)
- **Media**: Weekly on Sunday (7-day retention)
- **S3 Integration**: Optional off-site backup storage

```bash
# Manual backup
./scripts/backup/backup-database.sh
./scripts/backup/backup-media.sh
```

## API Documentation

Full API documentation available at `/api/docs/` when running the platform.

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/discovery/ml/classify/` | POST | Classify text for sensitive data |
| `/api/discovery/ml/batch-classify/` | POST | Batch classification |
| `/api/discovery/ml/feedback/` | POST | Submit classification feedback |
| `/api/discovery/ml/feedback/stats/` | GET | Get accuracy metrics |
| `/api/discovery/ml/training-data/` | GET/POST | Manage training data |
| `/api/discovery/jobs/` | GET/POST | Discovery job management |
| `/health/` | GET | Comprehensive health check |
| `/api/metrics/` | GET | Prometheus metrics |

## Project Structure

```
datadestroyer/
├── accounts/           # User authentication and authorization
├── analytics/          # Analytics and reporting
├── core/              # Core utilities and health checks
├── discovery/         # Data discovery and ML classification
│   ├── ml/           # ML engine (regex + spaCy)
│   ├── ml_models.py  # Django models for ML
│   └── ml_views.py   # ML API endpoints
├── destroyer/         # Django project settings
├── documents/         # Document management
├── moderation/        # Content moderation
├── monitoring/        # Prometheus and Grafana configs
├── nginx/            # Nginx reverse proxy config
├── scripts/          # Deployment and backup scripts
│   ├── deploy/      # Automated deployment
│   └── backup/      # Backup automation
├── docs/             # Documentation
│   ├── deployment/  # Deployment guides
│   └── architecture/ # Architecture documentation
└── tests/            # Test suite
```

## Performance

### Benchmarks

- **Response Time**: < 500ms average (99th percentile < 2s)
- **ML Classification**: ~100 texts/second (batch mode)
- **Database Queries**: < 100ms average
- **Cache Hit Rate**: 95%+

### Scaling

```bash
# Scale web workers
docker-compose up -d --scale web=4

# Scale Celery workers
docker-compose up -d --scale celery-worker=8
```

## Security

- **SSL/TLS**: A+ rating with modern ciphers
- **Security Headers**: HSTS, CSP, X-Frame-Options
- **Rate Limiting**: Configurable per-endpoint limits
- **RBAC**: Role-based access control
- **Audit Logging**: Comprehensive activity tracking
- **Secrets Management**: Environment variable encryption
- **Dependency Scanning**: Automated vulnerability checks

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/datadestroyer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/datadestroyer/discussions)

## Acknowledgments

Built with:
- [Django](https://www.djangoproject.com/) - Web framework
- [spaCy](https://spacy.io/) - NLP and NER
- [PostgreSQL](https://www.postgresql.org/) - Database
- [Redis](https://redis.io/) - Caching and message broker
- [Prometheus](https://prometheus.io/) - Metrics
- [Grafana](https://grafana.com/) - Dashboards
- [Docker](https://www.docker.com/) - Containerization

---

<div align="center">

**[Documentation](docs/)** • **[API Docs](https://yourdomain.com/api/docs/)** • **[Contributing](CONTRIBUTING.md)** • **[License](LICENSE)**


</div>
