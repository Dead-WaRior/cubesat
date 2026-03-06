.PHONY: start stop test lint build clean

start:
	docker compose up -d

stop:
	docker compose down

test:
	pytest tests/ -v --tb=short

lint:
	ruff check . --exclude dashboard

build:
	docker compose build

clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
