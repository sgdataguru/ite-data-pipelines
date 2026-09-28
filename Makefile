# ITE Data Pipelines workshop - common commands.
# Run "make <target>" from the repository root.

PYTHON ?= python
PID_FILE = logs/api.pid
scenario ?=
schemas ?=

.PHONY: check api api-stop fail init reset bronze dbt-reference pii-check

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
