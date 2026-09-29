"""DAG integrity test: every DAG in dags/ loads, and the two workshop DAGs exist.

Run with:  make dag-test
(It uses the Airflow venv's Python, because Airflow is not installed in the
main environment.)

A typo or a bad import in any DAG file shows up here as an import error,
with the file name and line number, before Airflow ever tries to run it.
"""

import sys
from pathlib import Path

DAGS = Path(__file__).resolve().parents[1] / "dags"
sys.path.insert(0, str(DAGS))   # Airflow does this itself when it runs; pytest does not

from airflow.models import DagBag  # noqa: E402  (must come after the sys.path line)


def test_dags_load_without_errors():
    bag = DagBag(dag_folder=str(DAGS))
    # On failure, print each broken file with its full error (file name and line).
    report = "\n\n".join(f"{path}\n{error}" for path, error in bag.import_errors.items())
    assert not bag.import_errors, "DAG import errors:\n\n" + report


def test_expected_dags_present():
    bag = DagBag(dag_folder=str(DAGS))
    assert {"capstone_pipeline", "reference_pipeline"} <= set(bag.dags)
