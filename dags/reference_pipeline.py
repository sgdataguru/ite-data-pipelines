"""reference_pipeline: the complete Day 3 example DAG.

It runs the whole ITE Student Analytics pipeline once a day at 06:00
Singapore time:

    ingest_files  ─┐
    ingest_database├─> dbt_build ─> record_run
    ingest_api    ─┘

Grain: ONE DAG run = ONE day of data. Each run loads whatever is new in the
three sources, rebuilds the reference dbt project (dbt/reference) and writes
one row to audit.pipeline_runs.

It is paused when Airflow first sees it. Unpause it in the Airflow UI when
you want it to run. Your own version is dags/capstone_pipeline.py.
"""

import os
from datetime import timedelta
from pathlib import Path

import pendulum
from airflow.sdk import dag, task
from pipeline_alerts import on_failure, on_retry

# The repository root. "make airflow" sets REPO_DIR; if it is missing we
# work it out from this file's location (dags/ is one folder below the root).
REPO = os.environ.get("REPO_DIR", str(Path(__file__).resolve().parents[1]))


def main_program(variable):
    """Absolute path of the main Python or dbt, set by "make airflow".

    Why absolute paths? Airflow lives in its own virtual environment
    (/opt/airflow-venv). While Airflow runs, a plain "python" or "dbt" would
    find the Airflow venv first, and that venv has no DuckDB and no dbt.
    "make airflow" looks up the MAIN python and dbt before starting Airflow
    and passes their full paths in MAIN_PYTHON and DBT_BIN.

    This is only called when a task RUNS, never when Airflow reads the file,
    so the DAG still loads (and the DAG test still passes) without them.
    """
    value = os.environ.get(variable)
    if not value:
        raise RuntimeError(f"{variable} is not set. Start Airflow with make airflow.")
    return value


default_args = {
    "owner": "ite-data-team",
    # Two layers of retry:
    #   1. Inside ingest_api, tenacity retries single requests when the API
    #      is busy or down (HTTP 429 or 5xx), for up to 2 minutes.
    #   2. Here, Airflow retries the WHOLE task when it fails for any other
    #      reason, e.g. a rejected token (HTTP 401) or a locked warehouse.
    "retries": 3,
    "retry_delay": timedelta(minutes=1),
    "retry_exponential_backoff": True,   # wait longer after each failed try
    "execution_timeout": timedelta(minutes=20),
    # DuckDB allows ONE writer at a time. Every task writes to the warehouse,
    # so they all share the 1-slot "duckdb" pool: Airflow runs them one after
    # the other instead of letting them fight over the file lock.
    "pool": "duckdb",
    "on_retry_callback": on_retry,       # a try failed and will be retried
    "on_failure_callback": on_failure,   # the last try failed
}


@dag(
    dag_id="reference_pipeline",
    schedule="0 6 * * *",                # every day at 06:00
    start_date=pendulum.datetime(2026, 1, 1, tz="Asia/Singapore"),
    catchup=False,                       # do not back-fill the days since start_date
    is_paused_upon_creation=True,
    default_args=default_args,
    tags=["capstone"],
)
def reference_pipeline():

    # Each task returns a shell command. Airflow runs it in the repository
    # folder with the MAIN Python, so the Day 1 and Day 2 scripts work as-is.

    @task.bash
    def ingest_files():
        return f"cd {REPO} && {main_program('MAIN_PYTHON')} lab1/solution/ingest_files.py"

    @task.bash
    def ingest_database():
        return f"cd {REPO} && {main_program('MAIN_PYTHON')} lab1/solution/ingest_database.py"

    @task.bash
    def ingest_api():
        return f"cd {REPO} && {main_program('MAIN_PYTHON')} lab2/solution/ingest_api.py"

    @task.bash
    def dbt_build():
        return f"cd {REPO}/dbt/reference && {main_program('DBT_BIN')} build"

    @task.bash
    def record_run():
        # {{ run_id }} and {{ dag.dag_id }} are filled in by Airflow when the task runs.
        return (f"cd {REPO} && {main_program('MAIN_PYTHON')} scripts/record_run.py "
                "--run-id '{{ run_id }}' --dag-id {{ dag.dag_id }} --dbt-dir dbt/reference")

    # The three loads can run in any order; dbt waits for all three.
    [ingest_files(), ingest_database(), ingest_api()] >> dbt_build() >> record_run()


reference_pipeline()
