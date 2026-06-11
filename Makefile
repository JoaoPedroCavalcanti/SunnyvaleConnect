.PHONY: help install test test-cov test-docker test-fast lint schema schema-docker clean

SCHEMA_FILE ?= schema.yml
MYAPP_CONTAINER ?= myapp

help:
	@echo "Common targets:"
	@echo "  make install        Install Poetry deps (incl. dev)"
	@echo "  make test           Run the full test suite (SQLite in-memory)"
	@echo "  make test-cov       Same as 'test' + coverage report + coverage.xml"
	@echo "  make test-fast      Run tests with -x --ff (stop on first failure)"
	@echo "  make test-docker    Run tests inside the docker-compose 'test' service"
	@echo "  make schema         Generate OpenAPI schema (uses local Poetry env)"
	@echo "  make schema-docker  Generate OpenAPI schema inside the running 'myapp' container"
	@echo "  make clean          Remove caches, coverage artefacts"

install:
	cd myapp && poetry install --with dev

test:
	cd myapp && TESTING=1 poetry run pytest

test-cov:
	bash scripts/test.sh

test-fast:
	cd myapp && TESTING=1 poetry run pytest -x --ff

test-docker:
	docker compose --profile test run --rm test

schema:
	cd myapp && TESTING=1 poetry run python manage.py spectacular --file ../$(SCHEMA_FILE)
	@echo "OpenAPI schema written to $(SCHEMA_FILE)"

schema-docker:
	docker exec $(MYAPP_CONTAINER) sh -c "cd /myapp && TESTING=1 python manage.py spectacular --file /tmp/schema.yml"
	docker cp $(MYAPP_CONTAINER):/tmp/schema.yml ./$(SCHEMA_FILE)
	@echo "OpenAPI schema written to $(SCHEMA_FILE)"

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	rm -f myapp/.coverage myapp/coverage.xml
