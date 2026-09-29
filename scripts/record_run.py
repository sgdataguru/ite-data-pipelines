"""Record one pipeline run in the warehouse: the run audit.

Called as the last task of each DAG:

    python scripts/record_run.py --run-id <run id> --dag-id <dag id> [--dbt-dir dbt]

Writes one row to audit.pipeline_runs with:
  - how many rows each Bronze table holds after the run,
  - how many attendance rows were quarantined (bronze.file_attendance_rejects),
  - the dbt test results (PASS / WARN / ERROR) from <dbt-dir>/target/run_results.json.

Comparing these rows day by day is how you spot a run that is "green" but
did not load anything new.

Safe to run twice for the same run: the old row for that run_id is replaced.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb

# The repository root is one folder up from scripts/.
ROOT = Path(__file__).resolve().parent.parent
WAREHOUSE = ROOT / "warehouse" / "pipeline.duckdb"
SGT = ZoneInfo("Asia/Singapore")

# Row counts to record: column name in the audit table -> table to count.
ROW_COUNTS = {
    "rows_file_attendance": "bronze.file_attendance",
    "rows_db_students": "bronze.db_students",
    "rows_api_grades": "bronze.api_grades",
    "rows_quarantined": "bronze.file_attendance_rejects",
}


def count_rows(con, table):
    """Number of rows in schema.table, or None if the table does not exist."""
    schema, name = table.split(".")
    exists = con.execute("""
        SELECT count(*) FROM information_schema.tables
        WHERE table_schema = ? AND table_name = ?
    """, [schema, name]).fetchone()[0]
    if not exists:
        return None
    return con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def dbt_results(dbt_dir):
    """Count PASS, WARN and ERROR in dbt's run_results.json, like dbt's summary line.

    dbt writes "success" for models and seeds and "pass" for tests; both
    count as PASS. "error" and "fail" both count as ERROR.
    Returns (None, None, None) if the file does not exist yet.
    """
    results_file = ROOT / dbt_dir / "target" / "run_results.json"
    if not results_file.exists():
        print(f"Note: {results_file.relative_to(ROOT)} not found, dbt columns left empty")
        return None, None, None
    statuses = [r["status"] for r in json.loads(results_file.read_text())["results"]]
    passed = sum(s in ("success", "pass") for s in statuses)
    warned = sum(s == "warn" for s in statuses)
    errored = sum(s in ("error", "fail") for s in statuses)
    return passed, warned, errored


def main():
    parser = argparse.ArgumentParser(description="Record one pipeline run in audit.pipeline_runs")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dag-id", required=True)
    parser.add_argument("--dbt-dir", default="dbt", help="dbt project folder (default: dbt)")
    args = parser.parse_args()

    con = duckdb.connect(str(WAREHOUSE))
    con.execute("CREATE SCHEMA IF NOT EXISTS audit")
    con.execute("""
        CREATE TABLE IF NOT EXISTS audit.pipeline_runs (
            run_id               VARCHAR,
            dag_id               VARCHAR,
            recorded_at          TIMESTAMP,   -- Singapore time
            rows_file_attendance BIGINT,
            rows_db_students     BIGINT,
            rows_api_grades      BIGINT,
            rows_quarantined     BIGINT,
            dbt_pass             INTEGER,
            dbt_warn             INTEGER,
            dbt_error            INTEGER
        )
    """)

    row = {
        "run_id": args.run_id,
        "dag_id": args.dag_id,
        "recorded_at": datetime.now(SGT).replace(tzinfo=None, microsecond=0),
    }
    for column, table in ROW_COUNTS.items():
        row[column] = count_rows(con, table)
    row["dbt_pass"], row["dbt_warn"], row["dbt_error"] = dbt_results(args.dbt_dir)

    # Idempotent: remove any earlier row for this run, then insert the new one.
    # Both happen in one transaction, so nobody ever sees zero or two rows.
    columns = ", ".join(row)
    placeholders = ", ".join("?" for _ in row)
    con.execute("BEGIN TRANSACTION")
    con.execute("DELETE FROM audit.pipeline_runs WHERE run_id = ?", [args.run_id])
    con.execute(f"INSERT INTO audit.pipeline_runs ({columns}) VALUES ({placeholders})",
                list(row.values()))
    con.execute("COMMIT")
    con.close()

    print("Recorded run in audit.pipeline_runs:")
    for column, value in row.items():
        print(f"  {column:<21} {value}")


if __name__ == "__main__":
    main()
