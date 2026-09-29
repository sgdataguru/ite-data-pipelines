# Runbook: <pipeline name>

## Pipeline name and purpose

| Field | Value |
|---|---|
| Pipeline name | |
| Purpose (one sentence) | |
| Owner | |
| Backup owner | |
| Schedule | |
| Expected duration | |

## Where to look

| What | Where |
|---|---|
| Run status and task logs | Airflow UI (port 8080) → DAG → run → task → Logs |
| Retry and failure alerts | `logs/alerts.log` (and the webhook channel, if set) |
| Row counts and dbt results per run | `audit.pipeline_runs` in `warehouse/pipeline.duckdb` |
| Script logs | `logs/pipeline.log` |

## Alert: ingestion failed (API or token)

**First check:**

**Then:**

## Alert: DuckDB lock

**First check:**

**Then:**

## Alert: dbt tests failed

**First check:**

**Then:**

## Alert: run green but volumes wrong

**First check:**

**Then:**

## How to re-run safely

-

## How to roll back a bad change

1. Revert the pull request that introduced the change.
2. Wait for CI to pass on the revert.
3. Re-run the DAG and check `audit.pipeline_runs`.
