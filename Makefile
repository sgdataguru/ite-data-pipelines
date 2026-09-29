# ITE Data Pipelines workshop - common commands.
# Run "make <target>" from the repository root.

PYTHON ?= python

# dbt and DuckDB paths, worked out from this folder, so make targets work even
# in a Codespace that does not set them (or a renamed repository).
export DBT_PROFILES_DIR := $(CURDIR)/dbt
export DUCKDB_PATH := $(CURDIR)/warehouse/pipeline.duckdb

PID_FILE = logs/api.pid
scenario ?=
schemas ?=

.PHONY: check api api-stop fail init reset bronze dbt-reference pii-check \
        update airflow airflow-stop dag-test

# Check that tools, data and the mock API are ready
check:
	$(PYTHON) scripts/check.py

# Start the mock grades API in the background on port 8000
api:
	@mkdir -p logs
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		echo "Mock API is already running (PID $$(cat $(PID_FILE))). Nothing to do."; \
	else \
		nohup $(PYTHON) -m uvicorn mock_api.app:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 & \
		echo $$! > $(PID_FILE); \
		for i in $$(seq 1 20); do curl -sf localhost:8000/health > /dev/null && break; sleep 1; done; \
		echo "Mock API started on http://localhost:8000 (PID $$(cat $(PID_FILE))). Log: logs/api.log"; \
	fi

# Stop the mock grades API
api-stop:
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		kill $$(cat $(PID_FILE)); \
		while kill -0 $$(cat $(PID_FILE)) 2>/dev/null; do sleep 0.2; done; \
		rm -f $(PID_FILE); echo "Mock API stopped."; \
	else \
		rm -f $(PID_FILE); echo "Mock API was not running."; \
	fi

# Facilitator: switch on a failure scenario, e.g. make fail scenario=a
fail:
	$(PYTHON) scripts/fail.py $(scenario)

# Create the DuckDB warehouse and the empty Bronze tables
init:
	$(PYTHON) scripts/init_db.py

# Facilitator: drop all Bronze tables and start clean
reset:
	$(PYTHON) scripts/reset_db.py

# Day 2: populate Bronze by running the three Day 1 solution loaders.
# Safe to run more than once; makes sure the mock API is up first.
bronze:
	@$(MAKE) --no-print-directory api
	$(PYTHON) lab1/solution/ingest_files.py
	$(PYTHON) lab1/solution/ingest_database.py
	$(PYTHON) lab2/solution/ingest_api.py

# Day 2 (facilitator): build the reference dbt project.
dbt-reference:
	cd dbt/reference && dbt seed && dbt build
	@echo "make dbt-reference: seed + build finished (see the PASS/WARN/ERROR line above)"

# Day 2: check no schema (default: silver, gold, ref_silver, ref_gold) holds
# a readable NRIC-shaped value. Add schemas=<list> to scan somewhere else,
# e.g.  make pii-check schemas=bronze
pii-check:
	@if [ -n "$(schemas)" ]; then \
		$(PYTHON) scripts/pii_check.py --schemas $(schemas); \
	else \
		$(PYTHON) scripts/pii_check.py; \
	fi

# Bring the latest workshop files from the facilitators' template into your
# copy. Your own work (dbt/models, lab1, lab2, journal.md...) is never touched.
update:
	@bash scripts/update_from_template.sh

# ---------------------------------------------------------------------------
# Day 3: Airflow
# ---------------------------------------------------------------------------
# Paths are built from $(CURDIR) (the folder this Makefile is in), so they
# are correct even if your repository has a different name.
AIRFLOW_PYTHON = /opt/airflow-venv/bin/python

# Start Airflow in the background on port 8080 (log in logs/airflow.log).
# MAIN_PYTHON and DBT_BIN are looked up HERE, before scripts/airflow.sh puts
# the Airflow venv first on the PATH. The DAG tasks use these absolute paths.
airflow:
	@MAIN_PYTHON="$$(command -v $(PYTHON))" \
	DBT_BIN="$$(command -v dbt)" \
	REPO_DIR="$(CURDIR)" \
	DUCKDB_PATH="$(CURDIR)/warehouse/pipeline.duckdb" \
	DBT_PROFILES_DIR="$(CURDIR)/dbt" \
	AIRFLOW_HOME="$(CURDIR)/.airflow" \
	AIRFLOW__CORE__DAGS_FOLDER="$(CURDIR)/dags" \
	AIRFLOW__CORE__LOAD_EXAMPLES=False \
	AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_ALL_ADMINS=True \
	bash scripts/airflow.sh start

# Stop Airflow (only the processes "make airflow" started).
airflow-stop:
	@REPO_DIR="$(CURDIR)" bash scripts/airflow.sh stop

# Check every DAG in dags/ loads without errors. Runs with the Airflow venv's
# Python (pytest is installed there first if it is missing).
dag-test:
	@$(AIRFLOW_PYTHON) -c "import pytest" 2>/dev/null || \
		$(AIRFLOW_PYTHON) -m pip install -q "pytest==9.1.1"
	AIRFLOW_HOME="$(CURDIR)/.airflow" AIRFLOW__CORE__LOAD_EXAMPLES=False \
		$(AIRFLOW_PYTHON) -m pytest -q tests/test_dag_integrity.py
