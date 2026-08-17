.PHONY: setup venv install install-dev lint test run run-local run-local-bootstrap run-rebuild run-azurite run-azurite-bootstrap run-azure run-azure-bootstrap azurite-up azurite-down terraform-init terraform-validate

ENV_FILE ?=
ENV_FILE_ARG = $(if $(ENV_FILE),--env-file "$(ENV_FILE)",)

setup: venv install install-dev

venv:
	python3 -m venv .venv

install:
	. .venv/bin/activate && python -m pip install --upgrade pip && pip install -e ".[azure]"

install-dev:
	. .venv/bin/activate && pip install -r requirements-dev.txt

test:
	. .venv/bin/activate && pytest -q -s

run: run-local

run-local:
	. .venv/bin/activate && python -m pipeline.main --destination local $(ENV_FILE_ARG)

run-local-bootstrap:
	. .venv/bin/activate && python -m pipeline.main --destination local --full-refresh $(ENV_FILE_ARG)

run-rebuild:
	. .venv/bin/activate && python -m pipeline.main --destination local --force-rebuild $(ENV_FILE_ARG)

run-azurite:
	. .venv/bin/activate && python -m pipeline.main --destination azurite $(ENV_FILE_ARG)

run-azurite-bootstrap:
	. .venv/bin/activate && python -m pipeline.main --destination azurite --full-refresh $(ENV_FILE_ARG)

run-azure:
	. .venv/bin/activate && python -m pipeline.main --destination azure $(ENV_FILE_ARG)

run-azure-bootstrap:
	. .venv/bin/activate && python -m pipeline.main --destination azure --full-refresh $(ENV_FILE_ARG)

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
