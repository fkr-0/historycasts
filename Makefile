.PHONY: install test lint format-check lintfix coverage static live-static

install:
	uv sync --group dev

test:
	uv run pytest

lint:
	uv run ruff check src tests scripts
	uv run mypy

format-check:
	uv run ruff format src tests scripts --check

lintfix:
	uv run ruff check src tests scripts --fix
	uv run ruff format src tests scripts

coverage:
	uv run pytest --cov=src/podcast_atlas --cov-report=term-missing --cov-report=xml

static:
	uv run podcast-atlas build-static --db active.db --dataset-out static_site/dataset.json --web-dir frontend

live-static:
	./scripts/watch_static.sh
