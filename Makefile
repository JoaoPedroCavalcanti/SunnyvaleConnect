.PHONY: help install test test-cov test-docker test-fast lint clean

help:
	@echo "Common targets:"
	@echo "  make install        Install Poetry deps (incl. dev)"
	@echo "  make test           Run the full test suite (SQLite in-memory)"
	@echo "  make test-cov       Same as 'test' + coverage report + coverage.xml"
	@echo "  make test-fast      Run tests with -x --ff (stop on first failure)"
	@echo "  make test-docker    Run tests inside the docker-compose 'test' service"
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

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	rm -f myapp/.coverage myapp/coverage.xml
