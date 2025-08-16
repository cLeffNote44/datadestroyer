# Simple convenience Makefile for Unix-like environments

.PHONY: help dev up up-prod up-prod-tls down seed test lint fmt

help:
	@echo "Targets: dev, up, up-prod, up-prod-tls, down, seed, test, lint, fmt"

dev:
	docker compose up --build

up:
	docker compose up --build -d

up-prod:
	docker compose -f docker-compose.prod.yml up --build -d

up-prod-tls:
	docker compose -f docker-compose.prod.tls.yml up --build -d

down:
	docker compose down -v || true
	docker compose -f docker-compose.prod.yml down -v || true
	docker compose -f docker-compose.prod.tls.yml down -v || true

seed:
	docker compose exec web python manage.py seed_initial --username=admin --email=admin@example.com --password=ChangeMeNow!

test:
	. ./.venv/Scripts/activate 2>/dev/null || true; python -m pytest -q

lint:
	. ./.venv/Scripts/activate 2>/dev/null || true; python -m pre_commit run --all-files

fmt: lint
