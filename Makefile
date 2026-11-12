SHELL := /bin/sh
DC := docker compose
RUN := $(DC) run --rm -T tools
TASK ?= RL-01
MODE ?= golden
SCENARIO ?= INC-02
.PHONY: help up down migrate seed api worker test test-unit test-integration test-concurrency test-security lint typecheck format-check security-check invariants reconcile scenario challenge validate-tasks benchmark load-test ci reset-demo clean-artifacts
help:
	@echo "up down migrate seed api worker test test-unit test-integration test-concurrency test-security lint typecheck format-check security-check invariants reconcile scenario challenge validate-tasks benchmark load-test ci reset-demo clean-artifacts"
up:
	python3 scripts/bootstrap.py
	$(DC) up --build -d --wait api
migrate:
	$(DC) run --rm migrate
seed:
	$(RUN) -m banking_lab.cli seed
down:
	$(DC) down
api:
	$(DC) up -d --wait api
worker:
	$(DC) --profile worker up -d worker
test:
	$(RUN) scripts/run_tests.py -q --junitxml=artifacts/tests.xml
test-unit:
	$(RUN) -m pytest tests/unit -q
test-integration:
	$(RUN) scripts/run_tests.py tests/integration -q
test-concurrency:
	$(RUN) scripts/run_tests.py tests/concurrency -q
test-security:
	$(RUN) scripts/run_tests.py tests/security -q
lint:
	$(DC) run --rm -T --entrypoint ruff tools check src tests scripts benchmark
format-check:
	$(DC) run --rm -T --entrypoint ruff tools format --check src tests scripts benchmark alembic
typecheck:
	$(DC) run --rm -T --entrypoint mypy tools
security-check:
	$(DC) run --rm -T --entrypoint uv tools export --locked --no-dev --no-emit-project -o /tmp/lab-requirements.txt
	$(RUN) scripts/audit.py
invariants reconcile:
	$(RUN) -m banking_lab.cli reconcile
scenario:
	python3 scripts/scenario_runner.py $(SCENARIO)
challenge:
	python3 -m benchmark.cli run --task $(TASK) --mode $(MODE)
validate-tasks:
	python3 -m benchmark.cli validate
benchmark:
	python3 -m benchmark.cli validate --task $(TASK)
load-test:
	$(RUN) scripts/load_profile.py
ci: lint format-check typecheck test invariants
reset-demo:
	@test "$(CONFIRM)" = "DESTROY_LOCAL_DEMO" || (echo "Run make reset-demo CONFIRM=DESTROY_LOCAL_DEMO; deletes local demo volume."; exit 1)
	$(DC) down -v
	$(MAKE) up migrate seed
clean-artifacts:
	python3 -c "import shutil; shutil.rmtree('artifacts',ignore_errors=True)"
