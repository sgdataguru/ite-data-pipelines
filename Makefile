# ITE Data Pipelines workshop - common commands.
# Run "make <target>" from the repository root.

PYTHON ?= python
PID_FILE = logs/api.pid
scenario ?=

.PHONY: check api api-stop fail init reset

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
