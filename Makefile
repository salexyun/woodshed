.PHONY: test lint

test:
	cd backend && uv run pytest
	cd frontend && npm test

lint:
	cd backend && uv run ruff check && uv run ruff format --check
	cd frontend && npx tsc --noEmit
