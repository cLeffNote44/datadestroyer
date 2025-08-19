# Content Moderation System

## Overview

The Content Moderation System provides comprehensive AI-powered content analysis and moderation capabilities for Django applications. It automatically detects and manages sensitive content including PII (Personal Identifiable Information), financial data, government identifiers, and custom patterns.

## 🚀 Key Features

- **AI-Powered Detection**: Advanced pattern matching for PII, financial data, and custom content types
- **Real-time Scanning**: Automatic content analysis on creation and updates
- **Smart Analytics**: Integration with existing analytics for compliance insights
- **Automated Workflows**: Configurable moderation actions (quarantine, notifications, blocking)
- **Admin Dashboard**: Complete administrative interface for review and management
- **Bulk Operations**: Efficient scanning of large content volumes
- **API Integration**: RESTful APIs for programmatic access
- **Comprehensive Testing**: Performance, accuracy, and integration test suites

## 📦 Installation

The moderation system is already integrated into your Django project. Ensure you have the required dependencies and run the migrations:

```bash
# Apply database migrations
python manage.py migrate moderation

# Load default moderation patterns (recommended)
python manage.py loaddata moderation/fixtures/default_patterns.json

# Run comprehensive system tests
python manage.py run_moderation_tests
```

## 🔧 Configuration

### Settings

Add moderation settings to your Django settings:

```python
# settings.py

# Moderation system configuration
MODERATION_SETTINGS = {
    'AUTO_SCAN_ENABLED': True,
    'QUARANTINE_HIGH_RISK': True,
    'NOTIFY_USERS': True,
    'ADMIN_NOTIFICATIONS': True,
    'MAX_CONTENT_LENGTH': 10000,
    'BULK_SCAN_BATCH_SIZE': 100,
}

# Email configuration for notifications
DEFAULT_FROM_EMAIL = 'noreply@yourapp.com'
MODERATION_EMAIL_TEMPLATES = {
    'violation_detected': 'moderation/emails/violation.html',
    'content_quarantined': 'moderation/emails/quarantine.html',
    'bulk_scan_complete': 'moderation/emails/bulk_complete.html',
}
```

### URL Configuration

Include moderation URLs in your main URL configuration:

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path('api/moderation/', include('moderation.urls')),
    # ... your other URLs
]
```

## 🎯 Usage

### 1. Automatic Content Scanning

Content is automatically scanned when created or updated for registered models:

```python
# Models are automatically scanned via Django signals
document = Document.objects.create(
    title="My Document",
    content="This document contains SSN: 123-45-6789"  # Will be detected
)

# Scan results are available immediately
scan_result = ContentScan.objects.filter(
    content_type=ContentType.objects.get_for_model(Document),
    object_id=document.id
).first()
```

### 2. Manual Content Scanning

Scan content manually using the API or programmatically:

```python
from moderation.content_analyzer import ContentAnalyzer

analyzer = ContentAnalyzer()
result = analyzer.analyze_content("Email: user@example.com, Phone: 555-1234")

print(f"Violations detected: {len(result.violations)}")
print(f"Privacy score: {result.privacy_score}")
```

### 3. Bulk Scanning Operations

Use the management command for bulk scanning:

```bash
# Scan all content for a specific user
python manage.py bulk_scan_content --user-id 123

# Scan all users (use with caution)
python manage.py bulk_scan_content --all-users

# Dry run to see what would be scanned
python manage.py bulk_scan_content --all-users --dry-run
```

### 4. Admin Review Workflow

Access the admin interface for content review:

```python
# Via API endpoints
GET /api/moderation/admin/review-queue/
POST /api/moderation/admin/review-action/
GET /api/moderation/admin/dashboard/

# Via Django admin interface
# Navigate to /admin/moderation/
```

### 5. Analytics Integration

View moderation metrics in your analytics dashboard:

```python
from analytics.models import AnalyticsSnapshot

# Latest analytics with moderation data
snapshot = AnalyticsSnapshot.objects.latest('created_at')
print(f"Violations detected: {snapshot.violations_detected}")
print(f"Moderation compliance score: {snapshot.moderation_compliance_score}")
```

## 🔍 API Reference

### Content Scanning

```bash
# Scan specific content
POST /api/moderation/scan/
{
    "content": "Text to analyze",
    "content_type": "document",
    "object_id": 123
}

# Get scan results
GET /api/moderation/scans/{scan_id}/
```

### Pattern Management

```bash
# List detection patterns
GET /api/moderation/patterns/

# Create custom pattern
POST /api/moderation/patterns/
{
    "name": "Custom SSN Pattern",
    "pattern_type": "pii",
    "regex_pattern": "\\d{3}-\\d{2}-\\d{4}",
    "description": "Social Security Number detection"
}
```

### Admin Operations

```bash
# Review queue
GET /api/moderation/admin/review-queue/

# Approve content
POST /api/moderation/admin/review-action/
{
    "scan_ids": [1, 2, 3],
    "action": "approve",
    "notes": "Reviewed and approved"
}
```

## 🧪 Testing

The system includes comprehensive testing capabilities:

```bash
# Run all tests
python manage.py run_moderation_tests

# Run specific test types
python manage.py run_moderation_tests --test-type performance
python manage.py run_moderation_tests --test-type accuracy
python manage.py run_moderation_tests --test-type integration

# Run with benchmarking
python manage.py run_moderation_tests --benchmark
```

### Test Coverage

- **Performance Tests**: Content scanning speed, bulk operations, concurrent users
- **Accuracy Tests**: Detection precision, false positive/negative rates, edge cases
- **Integration Tests**: API functionality, end-to-end workflows, analytics integration

## 📊 Monitoring & Analytics

### Key Metrics

The system tracks important metrics:

- Total content scans performed
- Violations detected by type and severity
- Average processing time per scan
- User compliance scores
- Pattern effectiveness rates

### Analytics Dashboard

Access detailed analytics through:

1. **Django Admin**: `/admin/moderation/`
2. **API Dashboard**: `/api/moderation/dashboard/`
3. **Analytics Integration**: Moderation data in main analytics

### Performance Monitoring

Monitor system performance:

```python
from moderation.models import ContentScan

# Average processing times
avg_time = ContentScan.objects.aggregate(
    avg_time=models.Avg('processing_time_ms')
)['avg_time']

# Violation statistics
violation_stats = PolicyViolation.objects.values('severity').annotate(
    count=models.Count('id')
)
```

## 🔒 Security & Privacy

### Data Protection

- All sensitive content is encrypted in transit and at rest
- Scan results are automatically purged based on retention policies
- User data is anonymized in analytics where possible
- Access controls restrict admin operations to authorized users

### Compliance

The system helps maintain compliance with:

- **GDPR**: PII detection and privacy scoring
- **CCPA**: California consumer privacy protection
- **HIPAA**: Healthcare data identification (with custom patterns)
- **PCI DSS**: Financial data detection

## 🚀 Production Deployment

### Pre-deployment Checklist

1. **Run comprehensive tests**:
   ```bash
   python manage.py run_moderation_tests
   ```

2. **Validate production readiness**:
   ```python
   from moderation.management.commands.run_moderation_tests import validate_production_readiness

   is_ready, issues = validate_production_readiness()
   if not is_ready:
       print("Issues to resolve:", issues)
   ```

3. **Configure email settings** for notifications
4. **Set up monitoring** and alerting
5. **Load production patterns** and test with sample content
6. **Train administrators** on review workflows

### Performance Optimization

For production environments:

- Enable database indexing on scan tables
- Configure Redis for caching (if available)
- Set appropriate batch sizes for bulk operations
- Monitor memory usage during large scans
- Consider asynchronous processing for heavy workloads

### Scaling Considerations

- **Database**: Ensure adequate storage for scan history
- **Processing**: Consider celery for background task processing
- **Memory**: Monitor memory usage during bulk operations
- **Storage**: Plan for log retention and cleanup policies

## 🛠 Customization

### Custom Detection Patterns

Add organization-specific patterns:

```python
from moderation.models import SensitiveContentPattern

# Employee ID pattern
SensitiveContentPattern.objects.create(
    name="Employee ID",
    pattern_type="organization",
    regex_pattern=r"EMP\d{6}",
    severity="medium",
    description="Company employee identifier"
)
```

### Custom Workflows

Extend moderation workflows:

```python
from moderation.signals import content_violation_detected

@receiver(content_violation_detected)
def custom_violation_handler(sender, **kwargs):
    violation = kwargs['violation']
    scan = kwargs['scan']

    # Custom handling logic
    if violation.severity == 'high':
        # Send to security team
        notify_security_team(scan)
```

### Email Template Customization

Customize notification templates in your templates directory:

```html
<!-- templates/moderation/emails/violation.html -->
<h2>Content Violation Detected</h2>
<p>Dear {{ user.first_name }},</p>
<p>We detected sensitive content that requires review...</p>
```

## 📞 Support

### Troubleshooting

Common issues and solutions:

1. **Slow scanning performance**: Check pattern complexity and database indexes
2. **False positives**: Review and refine detection patterns
3. **Email notifications not sending**: Verify email configuration
4. **Database migrations failing**: Ensure proper database permissions

### Logging

Enable detailed logging:

```python
# settings.py
LOGGING = {
    'loggers': {
        'moderation': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}
```

### Getting Help

- Check the test results for system validation
- Review Django admin interface for detailed scan information
- Monitor system logs for error details
- Use the management command for system diagnostics

---

## 📝 License

This moderation system is part of your Django application. Ensure compliance with your application's licensing terms when using in production environments.

## 🎉 Congratulations!

Your content moderation system is now fully configured and ready for production use. The comprehensive test suite ensures reliability, and the integrated analytics provide valuable insights into your content compliance posture.

Run `python manage.py run_moderation_tests` to validate everything is working correctly!
