#!/usr/bin/env bash
# Start or stop Airflow for Day 3. Called by the Makefile:
#     make airflow         ->  scripts/airflow.sh start
#     make airflow-stop    ->  scripts/airflow.sh stop
#
# The Makefile exports REPO_DIR, MAIN_PYTHON, DBT_BIN, DUCKDB_PATH,
# DBT_PROFILES_DIR, AIRFLOW_HOME and the AIRFLOW__* settings before calling
# this script, so every Airflow process (and every task it runs) sees them.

set -euo pipefail

AIRFLOW_VENV_BIN=/opt/airflow-venv/bin
REPO_DIR=${REPO_DIR:?"Run this through make airflow"}
PID_FILE="$REPO_DIR/logs/airflow.pid"
LOG_FILE="$REPO_DIR/logs/airflow.log"
HEALTH_URL="http://localhost:8080/api/v2/monitor/health"
WAIT_SECONDS=180

# True if the PID file points at a live process.
is_running() {
  [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

start() {
  mkdir -p "$REPO_DIR/logs" "$AIRFLOW_HOME"

  if is_running; then
    echo "Airflow is already running (PID $(cat "$PID_FILE")). Nothing to do."
    return 0
  fi

  if [ ! -x "$AIRFLOW_VENV_BIN/airflow" ]; then
    echo "Airflow is not installed at /opt/airflow-venv. See requirements-airflow.txt."
    exit 1
  fi
  if [ -z "${MAIN_PYTHON:-}" ] || [ -z "${DBT_BIN:-}" ]; then
    echo "Could not find python or dbt on the PATH. Run: pip install -r requirements.txt"
    exit 1
  fi

  # MAIN_PYTHON and DBT_BIN were resolved by the Makefile BEFORE this line.
  # From here on, plain "python" means the Airflow venv's python, which has
  # no DuckDB or dbt. That is why the DAG tasks use the absolute paths.
  export PATH="$AIRFLOW_VENV_BIN:$PATH"

  echo "Starting Airflow (log: logs/airflow.log). Main Python: $MAIN_PYTHON"
  # setsid puts Airflow and all its child processes in their own process
  # group, so "make airflow-stop" can stop exactly that group and nothing else.
  setsid nohup airflow standalone > "$LOG_FILE" 2>&1 < /dev/null &
  echo $! > "$PID_FILE"

  # Wait for the web server's health check to answer, printing a dot every 3 s.
  printf "Waiting for Airflow to become healthy"
  local waited=0
  until curl -sf "$HEALTH_URL" > /dev/null 2>&1; do
    if [ "$waited" -ge "$WAIT_SECONDS" ] || ! is_running; then
      echo
      echo "Airflow did not become healthy. Last 20 lines of logs/airflow.log:"
      tail -n 20 "$LOG_FILE"
      exit 1
    fi
    printf "."
    sleep 3
    waited=$((waited + 3))
  done
  echo " healthy after about ${waited}s."

  # DuckDB allows one writer at a time, so every task that touches the
  # warehouse runs in this 1-slot pool. "pools set" is safe to repeat.
  airflow pools set duckdb 1 "DuckDB allows one writer at a time" > /dev/null
  echo "Pool 'duckdb' ready (1 slot)."

  echo "Airflow is ready on port 8080. Open the Ports tab and click the globe icon."
}

stop() {
  if ! is_running; then
    rm -f "$PID_FILE"
    echo "Airflow was not running."
    return 0
  fi
  local pid
  pid=$(cat "$PID_FILE")
  # A minus sign before the PID means "the whole process group".
  kill -TERM -- "-$pid" 2>/dev/null || true
  # Give it up to 30 seconds to shut down cleanly, then force it.
  for _ in $(seq 1 30); do
    if ! pgrep -g "$pid" > /dev/null; then
      break
    fi
    sleep 1
  done
  if pgrep -g "$pid" > /dev/null; then
    kill -KILL -- "-$pid" 2>/dev/null || true
    sleep 1
  fi
  rm -f "$PID_FILE"
  echo "Airflow stopped."
}

case "${1:-}" in
  start) start ;;
  stop)  stop ;;
  *) echo "Usage: scripts/airflow.sh start|stop"; exit 1 ;;
esac
