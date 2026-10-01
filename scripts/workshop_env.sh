# Workshop environment variables, worked out from where the repository is.
#
# Codespaces created from an early copy of the template do not set
# DBT_PROFILES_DIR or DUCKDB_PATH, and a renamed repository gets the wrong
# paths. "make update" adds one line to ~/.bashrc that sources this file, so
# every new terminal gets the right values. To use it in the current terminal:
#     source scripts/workshop_env.sh

ITE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Paths: always taken from this repository, so they are right even if it was renamed.
export DBT_PROFILES_DIR="$ITE_ROOT/dbt"
export DUCKDB_PATH="$ITE_ROOT/warehouse/pipeline.duckdb"
export AIRFLOW_HOME="$ITE_ROOT/.airflow"

# Workshop values: kept if the Codespace already sets them.
export SOURCE_API_TOKEN="${SOURCE_API_TOKEN:-workshop-token-not-a-real-secret}"
export PII_SALT="${PII_SALT:-workshop-salt-not-a-real-secret}"
export MOCK_API_URL="${MOCK_API_URL:-http://localhost:8000}"

# Airflow settings, so "airflow ..." commands typed in any terminal see the
# same DAGs and database as "make airflow". MAIN_PYTHON and DBT_BIN are the
# main environment's python and dbt (looked up before the Airflow venv is
# activated); the DAG tasks use them to run the lab scripts.
export REPO_DIR="$ITE_ROOT"
export AIRFLOW__CORE__DAGS_FOLDER="$ITE_ROOT/dags"
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_ALL_ADMINS=True
export AIRFLOW__DAG_PROCESSOR__REFRESH_INTERVAL=30   # new DAG files appear within ~30 s
case "$(command -v python)" in
  /opt/airflow-venv/*) ;;   # Airflow venv already active: keep the earlier values
  *) export MAIN_PYTHON="$(command -v python)" DBT_BIN="$(command -v dbt)" ;;
esac
