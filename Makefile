.PHONY: test lint

frontend/node_modules: frontend/package-lock.json
	cd frontend && npm ci

test: frontend/node_modules
	cd backend && uv run pytest
	cd frontend && npm exec --no -- vitest run

lint: frontend/node_modules
	cd backend && uv run ruff check && uv run ruff format --check
	cd frontend && npm exec --no -- tsc --noEmit
