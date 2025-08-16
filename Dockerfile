# Simple dev Dockerfile using Python slim and SQLite
# For local development; not optimized for production

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps (build essentials for some wheels, and libmagic for python-magic-bin fallback)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first to leverage docker layer cache
COPY requirements/ requirements/
# Replace windows-only dependency with linux-compatible alternative
RUN sed -i "s/python-magic-bin.*/python-magic>=0.4/" requirements/base.txt \
    [0m[0m&& python -m pip install --upgrade pip \
    [0m[0m&& pip install -r requirements/dev.txt

# Copy project
COPY . .

# Ensure entrypoint is executable and has LF endings
RUN chmod +x /app/entrypoint.sh \
    && sed -i 's/\r$//' /app/entrypoint.sh

# Create a non-root user (optional)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Entrypoint handles migrations before starting dev server
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
