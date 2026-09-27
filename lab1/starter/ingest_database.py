"""Lab 1, part 2: incremental load of the student database into Bronze.

Run from the repository root (after "make init"):

    python lab1/starter/ingest_database.py

Only rows changed since the last load should be copied. "Since the last
load" is the watermark: the newest updated_at value already in Bronze.
Running the script twice in a row should load nothing the second time.
"""

import sys

from common import get_connection, get_logger, new_batch_id

log = get_logger("ingest_database")


def main():
    con = get_connection()
    batch_id = new_batch_id()
    log.info("Starting database load, batch %s", batch_id)

    # Connect DuckDB to the SQLite source database, read-only.
    con.execute("INSTALL sqlite; LOAD sqlite;")
    con.execute("ATTACH 'sources/ops.db' AS ops (TYPE sqlite, READ_ONLY)")

    table_exists = con.sql("""
        SELECT count(*) FROM information_schema.tables
        WHERE table_schema = 'bronze' AND table_name = 'db_students'
    """).fetchone()[0]
    if not table_exists:
        log.error("bronze.db_students does not exist. Run: make init")
        sys.exit(1)

    # TODO: Find the watermark: the newest updated_at already in
    #   bronze.db_students. If the table is empty, max() returns NULL, so use
    #   coalesce(...) to fall back to TIMESTAMP '1900-01-01'.
    #   Replace None with: con.sql("""SELECT ...""").fetchone()[0]
    last = None
    log.info("Watermark (newest updated_at in Bronze): %s", last)

    before = con.sql("SELECT count(*) FROM bronze.db_students").fetchone()[0]

    # TODO: Add the three metadata columns after "SELECT *", in this order:
    #   now() AS _ingested_at, 'ops.students' AS _source_file, ? AS _batch_id
    #   Then pass [batch_id, last] instead of [last] (one value per ?, in order).
    con.execute("""
        INSERT INTO bronze.db_students
        SELECT *
        FROM ops.students
        WHERE updated_at > ?
    """, [last])

    after = con.sql("SELECT count(*) FROM bronze.db_students").fetchone()[0]
    log.info("Inserted %s new rows into bronze.db_students (total now %s)",
             after - before, after)
    con.close()


if __name__ == "__main__":
    main()
