# Real-Time Data Discovery & Classification Engine

A comprehensive, intelligent data discovery and classification system with automated governance workflows, real-time monitoring, and compliance validation.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation & Setup](#installation--setup)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Performance & Optimization](#performance--optimization)
- [Testing](#testing)
- [Governance & Compliance](#governance--compliance)
- [Monitoring & Alerts](#monitoring--alerts)
- [Contributing](#contributing)

## Overview

The Real-Time Data Discovery & Classification Engine is an enterprise-grade system designed to automatically discover, classify, and govern sensitive data across your Django applications. It provides intelligent content analysis, automated governance workflows, and comprehensive compliance reporting.

### Key Capabilities

- **Intelligent Classification**: Multi-algorithm classification engine supporting PII, PHI, financial data, credentials, and intellectual property
- **Real-Time Monitoring**: Django signal-based monitoring that automatically processes new and modified data
- **Automated Governance**: Policy-driven governance with auto-tagging, retention scheduling, and access control recommendations
- **Compliance Framework**: Built-in support for GDPR, HIPAA, PCI-DSS, and SOC2 compliance validation
- **Performance Optimized**: Caching, batch processing, and query optimization for enterprise scale
- **Comprehensive Testing**: 95%+ test coverage with performance benchmarking and load testing

## Features

### 🔍 Data Discovery
- Automatic discovery of data assets across Django models
- Content-aware scanning with context analysis
- Data lineage tracking and relationship mapping
- Metadata extraction and enrichment
- Scheduled and on-demand discovery jobs

### 🧠 Intelligent Classification
- Multi-type classification engine (regex, keyword, ML-ready, context-based)
- Confidence scoring and threshold management
- Custom classification rules and patterns
- Batch processing for high-volume data
- False positive reduction algorithms

### 🏛️ Automated Governance
- Policy-driven governance workflows
- Automatic tagging based on classification results
- Retention schedule automation with compliance integration
- Access control recommendations and risk scoring
- Data lifecycle management automation

### ⚡ Real-Time Processing
- Django signal-based real-time monitoring
- Configurable monitoring targets (apps, models, fields)
- Automatic classification triggering
- Alert generation for sensitive data discovery
- Background processing with error resilience

### 📊 Analytics & Reporting
- Discovery metrics integration with analytics system
- Compliance reporting across multiple frameworks
- Data classification distribution analysis
- Privacy scoring enhancements
- Executive dashboards and insights

### 🛡️ Security & Compliance
- Multi-framework compliance validation (GDPR, HIPAA, PCI-DSS, SOC2)
- Automated compliance checking and reporting
- Data retention policy enforcement
- Access audit trails and monitoring
- Sensitive data inventory and tracking

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │    │  Classification │    │   Governance    │
│                 │    │     Engine      │    │  Orchestrator   │
│ • Django Models │───▶│                 │───▶│                 │
│ • File Systems  │    │ • Regex Rules   │    │ • Auto-Tagging  │
│ • Databases     │    │ • ML Algorithms │    │ • Retention     │
│ • APIs          │    │ • Context Analysis│    │ • Access Control│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Real-Time     │    │   Data Assets   │    │   Compliance    │
│   Monitoring    │    │   & Results     │    │   Validation    │
│                 │    │                 │    │                 │
│ • Django Signals│    │ • Asset Metadata│    │ • GDPR/HIPAA    │
│ • Event Queue   │    │ • Classifications│    │ • Policy Engine │
│ • Alert System  │    │ • Data Lineage  │    │ • Audit Trails  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Components

1. **Data Discovery Scanner**: Scans Django models and extracts content for analysis
2. **Classification Engine**: Multi-algorithm engine for intelligent data classification
3. **Governance Orchestrator**: Automated workflow engine for policy enforcement
4. **Real-Time Monitor**: Signal-based monitoring for immediate data processing
5. **Compliance Validator**: Multi-framework compliance checking and validation
6. **Analytics Integrator**: Integration with analytics and reporting systems

## Installation & Setup

### Prerequisites
- Django 3.2+
- Python 3.8+
- PostgreSQL or MySQL (recommended for production)
- Redis (for caching and real-time processing)

### Installation

1. **Add to Django Project**
   ```python
   # settings.py
   INSTALLED_APPS = [
       ...
       'discovery',
       ...
   ]
   ```

2. **Configure Database**
   ```python
   # Recommended PostgreSQL configuration
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'your_database',
           'USER': 'your_user',
           'PASSWORD': 'your_password',
           'HOST': 'localhost',
           'PORT': '5432',
           'OPTIONS': {
               'MAX_CONNS': 20,
           }
       }
   }
   ```

3. **Setup Caching**
   ```python
   # settings.py - Redis recommended for production
   CACHES = {
       'default': {
           'BACKEND': 'django.core.cache.backends.redis.RedisCache',
           'LOCATION': 'redis://127.0.0.1:6379/1',
           'OPTIONS': {
               'CONNECTION_POOL_KWARGS': {
                   'max_connections': 20,
               }
           }
       }
   }
   ```

4. **Run Migrations**
   ```bash
   python manage.py makemigrations discovery
   python manage.py migrate discovery
   ```

5. **Initialize System**
   ```bash
   python manage.py initialize_discovery
   python manage.py loaddata discovery/fixtures/default_rules.json
   ```

### URL Configuration

```python
# urls.py
urlpatterns = [
    ...
    path('api/discovery/', include('discovery.urls')),
    ...
]
```

## Usage

### Basic Discovery Workflow

1. **Create Discovery Job**
   ```python
   from discovery.models import DiscoveryJob
   
   job = DiscoveryJob.objects.create(
       name="User Data Discovery",
       description="Scan user-related models for sensitive data",
       job_type='targeted_scan',
       target_model='auth.user',
       schedule_type='manual'
   )
   ```

2. **Run Discovery**
   ```bash
   python manage.py run_discovery --job-id 1
   ```

3. **View Results**
   ```python
   from discovery.models import DataAsset, ClassificationResult
   
   # Get discovered assets
   assets = DataAsset.objects.filter(is_active=True)
   
   # Get classification results
   results = ClassificationResult.objects.filter(
       confidence_score__gte=0.8
   )
   ```

### Real-Time Monitoring Setup

1. **Create Monitor**
   ```python
   from discovery.models import RealTimeMonitor
   
   monitor = RealTimeMonitor.objects.create(
       name="User Profile Monitor",
       description="Monitor user profile changes",
       monitor_type='model_changes',
       target_specification={
           'apps': ['accounts'],
           'models': [
               {'app': 'accounts', 'model': 'profile'}
           ]
       },
       auto_classify=True,
       alert_on_sensitive=True,
       is_active=True
   )
   ```

2. **Automatic Processing**
   ```python
   # Real-time monitoring happens automatically via Django signals
   # When a Profile object is created/updated, it will be:
   # 1. Discovered as a DataAsset
   # 2. Classified for sensitive content
   # 3. Have governance policies applied
   # 4. Generate alerts if sensitive data is found
   ```

### Custom Classification Rules

```python
from discovery.models import ClassificationRule

# Create custom PII detection rule
ClassificationRule.objects.create(
    name="Custom Email Pattern",
    description="Detect email addresses with company domain",
    rule_type='regex',
    pattern=r'\b[A-Za-z0-9._%+-]+@yourcompany\.com\b',
    classification_type='PII',
    confidence_weight=0.85,
    metadata={
        'company_specific': True,
        'data_type': 'email',
        'sensitivity': 'high'
    },
    is_active=True
)
```

### Governance Workflows

```python
from discovery.governance import GovernanceOrchestrator

orchestrator = GovernanceOrchestrator()

# Apply governance to a classification result
classification = ClassificationResult.objects.get(id=1)
result = orchestrator.process_classification_result(classification)

# Run retention sweep
sweep_result = orchestrator.run_retention_sweep(dry_run=True)

# Generate compliance report
compliance_report = orchestrator.generate_compliance_report(
    framework='GDPR'
)
```

## API Reference

### Discovery Dashboard API

**Endpoint**: `GET /api/discovery/dashboard/`

**Response**:
```json
{
  "summary": {
    "total_assets": 1250,
    "recent_assets_24h": 45,
    "discovery_jobs_7d": 12,
    "successful_jobs_7d": 11,
    "active_monitors": 8,
    "recent_events_24h": 234,
    "recent_alerts_24h": 3
  },
  "classification_distribution": {
    "PII": 340,
    "PHI": 120,
    "FINANCIAL": 85,
    "PUBLIC": 705
  },
  "system_health": {
    "classification_engine_status": "active",
    "monitoring_status": "active",
    "last_scan_time": "2023-12-07T10:30:00Z"
  }
}
```

### Governance Dashboard API

**Endpoint**: `GET /api/discovery/governance-dashboard/`

**Query Parameters**:
- `framework` (optional): Filter by compliance framework (GDPR, HIPAA, PCI_DSS, SOC2)

**Response**:
```json
{
  "governance_overview": {
    "total_assets": 1250,
    "assets_with_governance": 892,
    "governance_coverage": 0.714,
    "assets_with_retention": 756,
    "retention_coverage": 0.605,
    "assets_due_for_retention": 12
  },
  "compliance": {
    "overall_score": 0.847,
    "compliant_assets": 1058,
    "non_compliant_assets": 192,
    "framework_scores": {
      "GDPR": 0.823,
      "HIPAA": 0.891,
      "PCI_DSS": 0.776
    },
    "top_violations": [
      {"violation": "Missing: encryption_at_rest", "count": 45},
      {"violation": "Missing: retention_limits", "count": 32}
    ]
  }
}
```

### Management Commands

```bash
# Run discovery scan
python manage.py run_discovery [--job-id ID] [--target-model MODEL] [--batch-size SIZE]

# Initialize monitoring system  
python manage.py initialize_monitoring [--create-defaults]

# Run governance workflows
python manage.py run_governance [--dry-run] [--asset-id ID] [--batch-size SIZE]

# Generate compliance report
python manage.py run_governance --compliance-report [--framework FRAMEWORK] [--output-file FILE]

# Run retention sweep
python manage.py run_governance --retention-sweep [--dry-run]

# Optimize system performance
python manage.py optimize_discovery [--vacuum-db] [--rebuild-indexes]
```

## Configuration

### Discovery Settings

```python
# settings.py
DISCOVERY_SETTINGS = {
    # Classification thresholds
    'CLASSIFICATION_MIN_CONFIDENCE': 0.7,
    'HIGH_CONFIDENCE_THRESHOLD': 0.9,
    
    # Real-time monitoring
    'ENABLE_REAL_TIME_MONITORING': True,
    'MONITORING_BATCH_SIZE': 50,
    'MONITORING_BATCH_TIMEOUT': 5.0,
    
    # Governance automation
    'AUTO_APPLY_GOVERNANCE': True,
    'GOVERNANCE_CONFIDENCE_THRESHOLD': 0.8,
    
    # Performance optimization
    'ENABLE_QUERY_CACHING': True,
    'CACHE_TIMEOUT': 900,  # 15 minutes
    'BATCH_UPDATE_SIZE': 100,
    
    # Data retention
    'DEFAULT_RETENTION_DAYS': 2555,  # 7 years
    'CLEANUP_RETENTION_DAYS': 90,
    
    # Compliance frameworks
    'ENABLED_FRAMEWORKS': ['GDPR', 'HIPAA', 'PCI_DSS'],
    
    # Alert settings  
    'ALERT_HIGH_RISK_CLASSIFICATIONS': True,
    'ALERT_CONFIDENCE_THRESHOLD': 0.85,
    'ALERT_EMAIL_NOTIFICATIONS': True,
}
```

### Logging Configuration

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'discovery': {
            'format': '[DISCOVERY] {levelname} {asctime} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'discovery_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/discovery.log',
            'formatter': 'discovery',
        },
    },
    'loggers': {
        'discovery': {
            'handlers': ['discovery_file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## Performance & Optimization

### Performance Monitoring

The system includes comprehensive performance monitoring:

```python
from discovery.optimization import monitor_performance

@monitor_performance
def your_function():
    # Function execution time and query count will be monitored
    pass
```

### Optimization Features

1. **Database Optimizations**
   - Automatic index creation for common query patterns
   - Query optimization and caching
   - Bulk operations for batch processing

2. **Classification Engine Optimization**
   - Regex pattern pre-compilation
   - Rule caching and grouping
   - Batch classification processing

3. **Real-Time Processing Optimization**
   - Event batching and queue management
   - Monitor caching for faster access
   - Background processing with threading

### Performance Benchmarks

Run performance benchmarks:

```bash
python -m discovery.tests.test_runner
```

Expected performance targets:
- Classification: >100 items/second
- API Response: <2 seconds average
- Governance Processing: >50 assets/second
- Memory Usage: <100MB increase under load

## Testing

### Test Suite Overview

The system includes comprehensive testing with 95%+ coverage:

- **Classification Accuracy Tests**: Validate accuracy across data types
- **API Endpoint Tests**: Full API testing with security validation  
- **Integration Tests**: End-to-end workflow testing
- **Performance Tests**: Load testing and benchmarking
- **Real-Time Monitoring Tests**: Signal processing validation

### Running Tests

```bash
# Run all discovery tests
python manage.py test discovery.tests

# Run specific test modules
python manage.py test discovery.tests.test_classification_accuracy
python manage.py test discovery.tests.test_api_endpoints
python manage.py test discovery.tests.test_integration_realtime

# Run with custom test runner
python discovery/tests/test_runner.py

# Run performance benchmarks only
python -c "from discovery.tests import PerformanceBenchmarks; PerformanceBenchmarks.benchmark_classification_engine()"
```

### Test Configuration

```python
# test_settings.py
from .settings import *

# Test-specific settings
DISCOVERY_SETTINGS.update({
    'ENABLE_REAL_TIME_MONITORING': False,  # Disable for unit tests
    'AUTO_APPLY_GOVERNANCE': False,
    'CACHE_TIMEOUT': 1,  # Short cache for testing
})

# Use in-memory database for faster tests
DATABASES['default'] = {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': ':memory:',
}
```

## Governance & Compliance

### Supported Frameworks

1. **GDPR (General Data Protection Regulation)**
   - Data subject rights validation
   - Consent tracking requirements
   - Data minimization and purpose limitation
   - Retention limits and deletion rights

2. **HIPAA (Health Insurance Portability and Accountability Act)**
   - PHI classification and protection
   - Access control and audit requirements
   - Encryption and transmission security
   - Minimum necessary principle

3. **PCI-DSS (Payment Card Industry Data Security Standard)**
   - Financial data protection
   - Network security requirements
   - Regular testing and monitoring
   - Access control and authentication

4. **SOC2 (Service Organization Control 2)**
   - Security policies and procedures
   - Access control and change management
   - Monitoring and incident response
   - Risk assessment frameworks

### Governance Policies

Default governance policies are automatically applied based on classification:

```python
# Example: PII Protection Policy
{
    "name": "PII Protection",
    "classification_types": ["PII"],
    "confidence_threshold": 0.8,
    "actions": {
        "tags": ["sensitive", "personal-data", "gdpr-scope"],
        "retention_days": 2555,  # 7 years
        "access_level": "confidential",
        "compliance_requirements": ["GDPR"],
        "encryption_required": True,
        "audit_required": True
    }
}
```

### Custom Governance Policies

```python
from discovery.governance import GovernancePolicy, PolicyEnforcementEngine

# Create custom policy
policy = GovernancePolicy("Custom PHI Policy", ["PHI"], 0.95)
policy.add_tag("medical-data")
policy.set_retention(3650)  # 10 years
policy.set_access_level("restricted")
policy.add_compliance_requirement("HIPAA")

# Apply to policy engine
engine = PolicyEnforcementEngine()
engine.policies.append(policy)
```

## Monitoring & Alerts

### Real-Time Monitoring

Configure monitoring targets:

```python
from discovery.models import RealTimeMonitor

# Monitor all user-related models
RealTimeMonitor.objects.create(
    name="User Data Monitor",
    monitor_type='model_changes',
    target_specification={
        'apps': ['auth', 'accounts', 'profiles'],
        'sensitivity_threshold': 'medium'
    },
    auto_classify=True,
    alert_on_sensitive=True,
    alert_threshold='high',
    is_active=True
)
```

### Alert Configuration

```python
# Custom alert conditions
def custom_alert_condition(asset, classification):
    return (
        classification.classification_type in ['PII', 'PHI'] and
        classification.confidence_score >= 0.9 and
        asset.metadata.get('publicly_accessible', False)
    )
```

### Monitoring Dashboard

Access real-time monitoring data:

```python
from discovery.models import MonitoringEvent, DataDiscoveryInsight

# Recent monitoring events
recent_events = MonitoringEvent.objects.filter(
    created_at__gte=timezone.now() - timedelta(hours=24)
).order_by('-created_at')

# Unresolved security insights
alerts = DataDiscoveryInsight.objects.filter(
    insight_type='security',
    severity__in=['high', 'critical'],
    is_resolved=False
)
```

## Contributing

### Development Setup

1. **Clone Repository**
   ```bash
   git clone https://github.com/your-org/data-destroyer.git
   cd data-destroyer
   ```

2. **Setup Development Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements-dev.txt
   ```

3. **Run Development Setup**
   ```bash
   python manage.py migrate
   python manage.py loaddata discovery/fixtures/test_data.json
   python manage.py initialize_discovery
   ```

### Code Quality Standards

- **Testing**: Maintain >95% test coverage
- **Performance**: All API endpoints <2s response time
- **Security**: No sensitive data in logs or responses
- **Documentation**: Comprehensive docstrings and README updates

### Submitting Changes

1. Create feature branch: `git checkout -b feature/new-feature`
2. Run tests: `python manage.py test discovery.tests`
3. Run linting: `flake8 discovery/`
4. Update documentation as needed
5. Submit pull request with detailed description

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions:
- Documentation: [Wiki](https://github.com/your-org/data-destroyer/wiki)
- Issues: [GitHub Issues](https://github.com/your-org/data-destroyer/issues)  
- Discussions: [GitHub Discussions](https://github.com/your-org/data-destroyer/discussions)

---

**Real-Time Data Discovery & Classification Engine** - Intelligent data governance for the modern enterprise.
