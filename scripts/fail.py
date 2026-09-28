"""Facilitator: switch failure scenarios on and off.

Run with:  make fail scenario=<x>

    a          mock API returns HTTP 500 for 30 seconds, then recovers
    ratelimit  mock API refuses 2 out of every 3 requests with HTTP 429
    auth, e    mock API rejects the token with HTTP 401
    b          a corrupted attendance file appears in data/attendance/
    c          a new column appears in the student database
    dq         (Day 2) inject one grade with an out-of-range score
    off        everything back to normal
"""

import json
import shutil
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "mock_api" / "state.json"
ATTENDANCE = ROOT / "data" / "attendance"
FIXTURE = ROOT / "data" / "fixtures" / "attendance_corrupt.csv"
OPS_DB = ROOT / "sources" / "ops.db"
OPS_ORIGINAL = ROOT / "sources" / "ops_original.db"
WAREHOUSE = ROOT / "warehouse" / "pipeline.duckdb"

VALID = ["a", "b", "c", "dq", "ratelimit", "auth", "e", "off"]

# Five students who get a preferred name in Scenario C.
PREFERRED_NAMES = {
    "S0002": "Jayden", "S0007": "Pri", "S0015": "Ash",
    "S0023": "Rach", "S0031": "Anj",
}


def set_api_mode(mode):
    # set_at records when the mode was switched on. Mode "a" uses it to end
    # the outage after 30 seconds.
    state = {"mode": mode, "set_at": time.time()}
    STATE_FILE.write_text(json.dumps(state) + "\n")


def scenario_b():
    target = ATTENDANCE / "attendance_2026-09-14_injected.csv"
    shutil.copyfile(FIXTURE, target)


def scenario_c():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    con = sqlite3.connect(OPS_DB)
    columns = [row[1] for row in con.execute("PRAGMA table_info(students)")]
    if "preferred_name" not in columns:
        con.execute("ALTER TABLE students ADD COLUMN preferred_name TEXT")
    for student_id, name in PREFERRED_NAMES.items():
        con.execute(
            "UPDATE students SET preferred_name = ?, updated_at = ? WHERE student_id = ?",
            (name, now, student_id),
        )
    con.commit()
    con.close()


def scenario_dq():
    # Day 2 scenario: add one grade whose score (150) is outside 0-100.
    # The reference singular test assert_score_between_0_and_100 catches it.
    if not WAREHOUSE.exists():
        print("Run make bronze first")
        sys.exit(1)
    con = duckdb.connect(str(WAREHOUSE))
    api_grades_exists = con.execute("""
        SELECT count(*) FROM information_schema.tables
        WHERE table_schema = 'bronze' AND table_name = 'api_grades'
    """).fetchone()[0]
    if not api_grades_exists:
        print("Run make bronze first")
        con.close()
        sys.exit(1)
    con.execute("""
        INSERT INTO bronze.api_grades BY NAME
        SELECT 99999      AS record_id,
               'S0001'    AS student_id,
               'DE101'    AS module_code,
               'Project'  AS assessment,
               150        AS score,
               now()      AS updated_at,
               now()      AS _ingested_at,
               'scenario_dq' AS _source_file,
               'scenario_dq' AS _batch_id
    """)
    con.close()


def scenario_off():
    set_api_mode("off")
    for injected in ATTENDANCE.glob("*_injected.csv"):
        injected.unlink()
    shutil.copyfile(OPS_ORIGINAL, OPS_DB)
    # Also undo any Day 2 dq injection, if the warehouse exists.
    if WAREHOUSE.exists():
        con = duckdb.connect(str(WAREHOUSE))
        api_grades_exists = con.execute("""
            SELECT count(*) FROM information_schema.tables
            WHERE table_schema = 'bronze' AND table_name = 'api_grades'
        """).fetchone()[0]
        if api_grades_exists:
            con.execute("DELETE FROM bronze.api_grades WHERE _source_file = 'scenario_dq'")
        con.close()


def main():
    if len(sys.argv) != 2 or sys.argv[1].lower() not in VALID:
        print("Usage: make fail scenario=<x>   where <x> is one of: " + ", ".join(VALID))
        sys.exit(1)

    scenario = sys.argv[1].lower()
    if scenario == "a":
        set_api_mode("a")
        print("Scenario A: mock API now returns HTTP 500 for the next 30 seconds")
    elif scenario == "ratelimit":
        set_api_mode("ratelimit")
        print("Scenario ratelimit: mock API now refuses 2 of every 3 requests with HTTP 429")
    elif scenario in ("auth", "e"):
        set_api_mode(scenario)
        print(f"Scenario {scenario.upper()}: mock API now rejects the token with HTTP 401")
    elif scenario == "b":
        scenario_b()
        print("Scenario B: corrupted file added to data/attendance/ "
              "(attendance_2026-09-14_injected.csv)")
    elif scenario == "c":
        scenario_c()
        print("Scenario C: column preferred_name added to ops.students; "
              "5 students updated")
    elif scenario == "dq":
        scenario_dq()
        # This is the one scenario that doesn't say what changed - the whole
        # exercise for Block 2 is to find the injected row through the tests.
        print("Scenario DQ applied")
    elif scenario == "off":
        scenario_off()
        print("Scenario OFF: API mode off, injected files removed, ops.db restored")


if __name__ == "__main__":
    main()
