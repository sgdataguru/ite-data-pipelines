"""capstone_pipeline: YOUR Day 3 DAG.

Goal: the same daily pipeline as dags/reference_pipeline.py, but building
YOUR dbt project (dbt/) instead of the reference one:

    ingest_files  ─┐
    ingest_database├─> dbt_build ─> record_run
    ingest_api    ─┘

As shipped, only ingest_files is finished, and it runs. Work through the
TODOs from top to bottom. After each change, run  make dag-test  to check the
file still loads, then trigger the DAG in the Airflow UI.

It is paused when Airflow first sees it. Unpause it in the Airflow UI.
"""

import os
from pathlib import Path

import pendulum
from airflow.sdk import dag, task

# TODO (default_args): you will need these two imports. Move them up with the
# other imports (above this comment) when you write default_args.
#   from datetime import timedelta
#   from pipeline_alerts import on_failure, on_retry

# The repository root. "make airflow" sets REPO_DIR; if it is missing we
# work it out from this file's location (dags/ is one folder below the root).
REPO = os.environ.get("REPO_DIR", str(Path(__file__).resolve().parents[1]))


def main_program(variable):
    """Absolute path of the main Python (MAIN_PYTHON) or dbt (DBT_BIN).

    "make airflow" sets both. Plain "python" or "dbt" would find the Airflow
    virtual environment first, which has no DuckDB and no dbt.
    """
    value = os.environ.get(variable)
    if not value:
        raise RuntimeError(f"{variable} is not set. Start Airflow with make airflow.")
    return value


# TODO (default_args): make every task safe to run unattended.
# Hint: copy the idea from reference_pipeline.py: 3 retries, 1 minute apart,
# growing each time, a 20-minute timeout, the "duckdb" pool and both alert callbacks.
default_args = {
    "owner": "your-name",
}


@dag(
    dag_id="capstone_pipeline",
    schedule="0 6 * * *",                # every day at 06:00
    start_date=pendulum.datetime(2026, 1, 1, tz="Asia/Singapore"),
    catchup=False,                       # do not back-fill the days since start_date
    is_paused_upon_creation=True,
    default_args=default_args,
    tags=["capstone"],
)
def capstone_pipeline():

    # Finished: loads the attendance CSV files into bronze.file_attendance.
    # pool="duckdb" is set on this task already, because unpausing the DAG and
    # triggering it gives two runs at once, and DuckDB allows one writer at a
    # time. Once your default_args sets the pool for every task, you can remove it here.
    @task.bash(pool="duckdb")
    def ingest_files():
        return f"cd {REPO} && {main_program('MAIN_PYTHON')} lab1/solution/ingest_files.py"

    # TODO (ingest_database): add a task that runs lab1/solution/ingest_database.py.
    # Hint: it looks exactly like ingest_files, with a different script name.

    # TODO (ingest_api): add a task that runs lab2/solution/ingest_api.py.
    # Hint: same pattern again; the mock API must be running (make api).

    # TODO (dbt_build): add a task that runs "dbt build" in YOUR project folder, dbt/.
    # Hint: cd into {REPO}/dbt and use main_program('DBT_BIN') instead of plain dbt.

    # TODO (record_run): add a task that runs scripts/record_run.py.
    # Hint: pass --run-id '{{ run_id }}' --dag-id {{ dag.dag_id }} (--dbt-dir defaults to dbt).

    # TODO (dependencies): replace the line below so the three loads run first,
    # then dbt_build, then record_run.
    # Hint: [a(), b(), c()] >> d() >> e()
    ingest_files()


capstone_pipeline()
