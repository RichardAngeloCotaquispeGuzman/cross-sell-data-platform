.PHONY: setup venv install install-dev lint test run run-local run-rebuild run-azurite run-azurite-bootstrap azurite-up azurite-down terraform-init terraform-validate

setup: venv install install-dev

venv:
	python3 -m venv .venv

install:
	. .venv/bin/activate && python -m pip install --upgrade pip && pip install -e .

install-dev:
	. .venv/bin/activate && pip install -r requirements-dev.txt

test:
	. .venv/bin/activate && pytest -q

run: run-local

run-local:
	. .venv/bin/activate && python -m pipeline.main --destination local

run-rebuild:
	. .venv/bin/activate && python -m pipeline.main --destination local --force-rebuild

run-azurite:
	. .venv/bin/activate && python -m pipeline.main --destination azurite

run-azurite-bootstrap:
	. .venv/bin/activate && python -m pipeline.main --destination azurite --full-refresh

azurite-up:
	docker compose up -d azurite

azurite-down:
	docker compose down

lint:
	. .venv/bin/activate && ruff check src tests && python -m compileall -q src

terraform-init:
	cd infra/azure/terraform && ../../../.venv/bin/terraform init -backend=false

terraform-validate:
	cd infra/azure/terraform && ../../../.venv/bin/terraform fmt -check && ../../../.venv/bin/terraform validate
