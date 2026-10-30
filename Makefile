.PHONY: install-dev test lint typecheck check ci

install-dev:
	uv sync --extra dev

test:
	uv run --extra dev pytest -q

lint:
	uv run --extra dev ruff check .

typecheck:
	uv run --extra dev mypy src

check: lint typecheck test

ci: install-dev check
