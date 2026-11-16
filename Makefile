.PHONY: test lint types

# Integration tests need Postgres: run `docker compose up -d --wait db` first.
export TEST_DATABASE_URL ?= postgresql://woodshed:woodshed@localhost:5432/woodshed_test

frontend/node_modules: frontend/package-lock.json
	cd frontend && npm ci

test: frontend/node_modules
	cd backend && uv run pytest
	cd frontend && npm exec --no -- vitest run

lint: frontend/node_modules
	cd backend && uv run ruff check && uv run ruff format --check
	cd frontend && npm exec --no -- tsc --noEmit

# openapi-typescript needs TypeScript 5's compiler API, which TypeScript 7 dropped,
# so it runs pinned through npm exec instead of as a dev dependency.
types:
	uv run --directory backend python -c "import json; from woodshed.main import app; print(json.dumps(app.openapi()))" \
		| npm exec --yes --package=openapi-typescript@7.13.0 -- openapi-typescript -o frontend/src/api-schema.d.ts
