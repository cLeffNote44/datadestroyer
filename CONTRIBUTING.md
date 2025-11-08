# Contributing to Data Destroyer

Thank you for your interest in contributing to Data Destroyer! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### Reporting Bugs

Before creating a bug report, please check existing issues to avoid duplicates.

When reporting a bug, include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, Docker version)
- Relevant logs or error messages

### Suggesting Enhancements

Enhancement suggestions are welcome! Please include:
- Clear description of the proposed feature
- Use cases and benefits
- Any implementation ideas you have

### Pull Requests

1. **Fork the repository**

```bash
git clone https://github.com/yourusername/datadestroyer.git
cd datadestroyer
```

2. **Create a feature branch**

```bash
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements

3. **Set up development environment**

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements/dev.txt

# Run migrations
python manage.py migrate
```

4. **Make your changes**

- Write clear, self-documenting code
- Follow PEP 8 style guidelines
- Add/update tests for your changes
- Update documentation as needed

5. **Test your changes**

```bash
# Run tests
pytest

# Check coverage
pytest --cov=. --cov-report=html

# Run linters
black .
isort .
ruff check .
mypy .
```

6. **Commit your changes**

```bash
git add .
git commit -m "Brief description of changes"
```

Commit message guidelines:
- Use present tense ("Add feature" not "Added feature")
- Be concise but descriptive
- Reference issues when applicable (#123)

7. **Push to your fork**

```bash
git push origin feature/your-feature-name
```

8. **Open a Pull Request**

- Provide a clear title and description
- Reference related issues
- Describe the changes and why they're needed
- Include screenshots for UI changes

## Development Guidelines

### Code Style

- **Python**: Follow PEP 8, use Black for formatting
- **Imports**: Organize with isort
- **Type Hints**: Use type annotations where appropriate
- **Docstrings**: Use Google-style docstrings

Example:

```python
def classify_text(text: str, threshold: float = 0.5) -> list[dict]:
    """Classify text for sensitive data entities.

    Args:
        text: The text to classify
        threshold: Minimum confidence threshold (0.0-1.0)

    Returns:
        List of detected entities with confidence scores

    Raises:
        ValueError: If threshold is out of range
    """
    if not 0 <= threshold <= 1:
        raise ValueError("Threshold must be between 0 and 1")

    # Implementation
    return entities
```

### Testing

- Write tests for all new features
- Maintain or improve code coverage (target: 80%+)
- Use pytest fixtures for common setup
- Mock external dependencies

Example:

```python
import pytest
from discovery.ml.classifiers import EmailClassifier

@pytest.fixture
def email_classifier():
    return EmailClassifier()

def test_email_detection(email_classifier):
    """Test basic email detection."""
    text = "Contact me at john@example.com"
    entities = email_classifier.extract(text)

    assert len(entities) == 1
    assert entities[0].text == "john@example.com"
    assert entities[0].label == "EMAIL"
```

### Documentation

- Update README.md for new features
- Add docstrings to all functions and classes
- Update API documentation when changing endpoints
- Include code examples where helpful

### Database Migrations

- Create migrations for model changes
- Test migrations both forwards and backwards
- Never modify existing migrations
- Use descriptive migration names

```bash
python manage.py makemigrations --name add_ml_feedback_model discovery
```

### API Changes

- Maintain backward compatibility when possible
- Version breaking changes
- Update OpenAPI schema
- Document changes in CHANGELOG.md

## Project Structure

```
datadestroyer/
├── <app_name>/
│   ├── models.py          # Django models
│   ├── views.py           # API endpoints
│   ├── serializers.py     # DRF serializers
│   ├── urls.py            # URL routing
│   ├── admin.py           # Django admin
│   ├── tests/             # App-specific tests
│   │   ├── test_models.py
│   │   ├── test_views.py
│   │   └── test_serializers.py
│   └── management/        # Management commands
│       └── commands/
```

## Testing Checklist

Before submitting a PR, ensure:

- [ ] All tests pass (`pytest`)
- [ ] Code coverage is maintained/improved
- [ ] No linting errors (`ruff check .`)
- [ ] Code is formatted (`black .`, `isort .`)
- [ ] Type checking passes (`mypy .`)
- [ ] Documentation is updated
- [ ] Manual testing completed
- [ ] No sensitive data in commits

## Review Process

1. **Automated checks** - CI runs tests and linters
2. **Code review** - Maintainers review your changes
3. **Feedback** - Address any requested changes
4. **Approval** - At least one maintainer approval required
5. **Merge** - Maintainers will merge your PR

## Getting Help

- Check existing documentation in `docs/`
- Search existing issues
- Ask questions in discussions
- Reach out to maintainers

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- GitHub contributors page

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Data Destroyer!
