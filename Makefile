.PHONY: run seed test migrate lint

run:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

seed:
	uv run python -m app.seed all

test:
	uv run pytest

migrate:
	@for migration in supabase/migrations/*.sql; do \
		echo "Applying $$migration"; \
		uv run python -m app.db apply-sql "$$migration"; \
	done

lint:
	uv run ruff check app tests scripts
