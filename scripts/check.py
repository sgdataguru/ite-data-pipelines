"""Check that the workshop environment is ready.

Run with:  make check

Prints one line per check (OK, FAIL or INFO). Every FAIL comes with a one-line fix.
Exits with a non-zero code if anything failed.
"""

import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AIRFLOW_PYTHON = Path("/opt/airflow-venv/bin/python")

failures = 0


def ok(message):
    print(f"OK   {message}")


def fail(message, fix):
    global failures
    failures += 1
    print(f"FAIL {message}. Fix: {fix}")


def check_python():
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if version == "3.12":
        ok(f"Python {sys.version.split()[0]}")
    else:
        fail(f"Python is {version}, expected 3.12", "open the repository in its Codespace")


def check_duckdb():
    try:
        import duckdb
        ok(f"duckdb {duckdb.__version__}")
    except ImportError:
        fail("duckdb not installed", "pip install -r requirements.txt")


def check_dbt():
    try:
        from importlib.metadata import version
        dbt_version = f"dbt-core {version('dbt-core')}, dbt-duckdb {version('dbt-duckdb')}"
    except Exception:
        fail("dbt not installed", "pip install -r requirements.txt")
        return
    if shutil.which("dbt"):
        ok(dbt_version)
    else:
        fail("dbt is installed but the dbt command is not on PATH", "pip install -r requirements.txt")


def check_airflow():
    if not AIRFLOW_PYTHON.exists():
        fail("Airflow virtual environment not found at /opt/airflow-venv",
             "rebuild the Codespace, or see requirements-airflow.txt")
        return
    result = subprocess.run(
        [str(AIRFLOW_PYTHON), "-c",
         "from importlib.metadata import version; print(version('apache-airflow'))"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        ok(f"Airflow {result.stdout.strip()} (in /opt/airflow-venv)")
    else:
        fail("Airflow not installed in /opt/airflow-venv", "see requirements-airflow.txt")


def check_airflow_running():
    # Informational only: Airflow is started on Day 3, so "not running" is
    # normal on Days 1 and 2 and never counts as a failure.
    try:
        urllib.request.urlopen("http://localhost:8080/api/v2/monitor/health", timeout=3)
        print("OK   Airflow running")
    except Exception:
        print("INFO Airflow not running (start on Day 3 with make airflow)")


def check_token():
    if os.environ.get("SOURCE_API_TOKEN"):
        ok("SOURCE_API_TOKEN is set")
    else:
        fail("SOURCE_API_TOKEN is not set",
             "export SOURCE_API_TOKEN=workshop-token-not-a-real-secret")


def check_data():
    csv_files = sorted((ROOT / "data" / "attendance").glob("attendance_2026-09-*.csv"))
    csv_files = [f for f in csv_files if not f.name.endswith("_injected.csv")]
    ops_db = ROOT / "sources" / "ops.db"
    if len(csv_files) == 5 and ops_db.exists():
        ok("Data files present (5 attendance CSVs, sources/ops.db)")
    else:
        fail(f"Data files missing ({len(csv_files)} attendance CSVs, "
             f"ops.db {'found' if ops_db.exists() else 'missing'})",
             "python scripts/generate_data.py")


def check_api():
    url = os.environ.get("MOCK_API_URL", "http://localhost:8000") + "/health"
    try:
        urllib.request.urlopen(url, timeout=3)
        ok(f"Mock API reachable at {url}")
    except Exception:
        fail("mock API not running", "make api")


def main():
    check_python()
    check_duckdb()
    check_dbt()
    check_airflow()
    check_token()
    check_data()
    check_api()
    check_airflow_running()
    if failures:
        print(f"\n{failures} check(s) failed.")
        sys.exit(1)
    print("\nAll checks passed. You are ready.")


if __name__ == "__main__":
    main()
