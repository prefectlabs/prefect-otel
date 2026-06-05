set dotenv-load := false

test:
    uv run pytest

lint:
    uv run ruff format --check .
    uv run ruff check .

format:
    uv run ruff format .
    uv run ruff check --fix .

typecheck:
    uv run mypy prefect_opentelemetry tests

coverage:
    uv run coverage run -m pytest
    uv run coverage report

build:
    uv build

