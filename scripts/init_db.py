"""Create the workshop warehouse and the empty Bronze tables.

Run with:  make init

Creates warehouse/pipeline.duckdb (if it does not exist), the "bronze"
schema, and an EMPTY bronze.db_students table. Its columns are the same as
ops.students, in the same order, followed by three metadata columns:
_ingested_at, _source_file and _batch_id.

Safe to run more than once: nothing is dropped or overwritten.
"""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
WAREHOUSE = ROOT / "warehouse" / "pipeline.duckdb"
OPS_DB = ROOT / "sources" / "ops.db"


def init_bronze(con):
    """Create the bronze schema and the empty bronze.db_students table."""
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")

    # Read the column list from the source database, so Bronze always
    # matches ops.students exactly.
    con.execute("INSTALL sqlite; LOAD sqlite;")
    con.execute(f"ATTACH '{OPS_DB}' AS ops (TYPE sqlite, READ_ONLY)")

    # "LIMIT 0" copies the columns and their types, but no rows.
    con.execute("""
        CREATE TABLE IF NOT EXISTS bronze.db_students AS
        SELECT *,
               NULL::TIMESTAMP AS _ingested_at,
               NULL::VARCHAR   AS _source_file,
               NULL::VARCHAR   AS _batch_id
        FROM ops.students
        LIMIT 0
    """)
    con.execute("DETACH ops")


def main():
    WAREHOUSE.parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)
    con = duckdb.connect(str(WAREHOUSE))
    init_bronze(con)
    rows = con.sql("SELECT count(*) FROM bronze.db_students").fetchone()[0]
    con.close()
    print(f"Warehouse ready: {WAREHOUSE.relative_to(ROOT)} "
          f"(bronze.db_students has {rows} rows)")


if __name__ == "__main__":
    main()
