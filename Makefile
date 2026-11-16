.PHONY: up test lint types

# Integration tests need Postgres: run `docker compose up -d --wait db` first.
export TEST_DATABASE_URL ?= postgresql://woodshed:woodshed@localhost:5432/woodshed_test

up:
	docker compose up --build --wait

frontend/node_modules: frontend/package-lock.json
	cd frontend && npm ci

test: frontend/node_modules
	cd backend && uv run pytest
	cd frontend && npm exec --no -- vitest run

lint: frontend/node_modules
	cd backend && uv run ruff check . ../incident-response && uv run ruff format --check . ../incident-response
	cd frontend && npm exec --no -- tsc --noEmit

# openapi-typescript needs TypeScript 5's compiler API, which TypeScript 7 dropped,
# so it lives in its own locked package instead of as a frontend dev dependency.
frontend/tools/openapi/node_modules: frontend/tools/openapi/package-lock.json
	npm ci --prefix frontend/tools/openapi

types: frontend/tools/openapi/node_modules
	uv run --directory backend python -c "import json; from woodshed.main import app; print(json.dumps(app.openapi()))" \
		| frontend/tools/openapi/node_modules/.bin/openapi-typescript -o frontend/src/api-schema.d.ts
