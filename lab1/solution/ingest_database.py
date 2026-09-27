"""Lab 1, part 2: incremental load of the student database into Bronze.

Run from the repository root (after "make init"):

    python lab1/solution/ingest_database.py

Only rows changed since the last load are copied. "Since the last load" is
the watermark: the newest updated_at value already in Bronze. Running the
script twice in a row loads nothing the second time (idempotent).
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

    # The watermark: the newest updated_at we already have.
    # If Bronze is empty, start from the beginning of time.
    last = con.sql("""SELECT coalesce(max(updated_at), TIMESTAMP '1900-01-01')
                      FROM bronze.db_students""").fetchone()[0]
    log.info("Watermark (newest updated_at in Bronze): %s", last)

    before = con.sql("SELECT count(*) FROM bronze.db_students").fetchone()[0]

    # --- Lab 1 version -------------------------------------------------------
    # This plain INSERT matches columns by POSITION. It breaks as soon as the
    # source table gains a column (Lab 3, Scenario C). Compare it with the
    # fixed version below.
    #
    # con.execute("""
    #     INSERT INTO bronze.db_students
    #     SELECT *, now() AS _ingested_at,
    #            'ops.students' AS _source_file, ? AS _batch_id
    #     FROM ops.students
    #     WHERE updated_at > ?
    # """, [batch_id, last])
    # -------------------------------------------------------------------------

    # --- Lab 3 fix: handle a new column in the source ------------------------
    # 1. Compare the source columns with the Bronze columns.
    source_columns = con.sql("DESCRIBE ops.students").fetchall()
    bronze_names = [row[0] for row in con.sql("DESCRIBE bronze.db_students").fetchall()]

    # 2. If the source has a column Bronze does not, add it to Bronze.
    for column_name, column_type, *_ in source_columns:
        if column_name not in bronze_names:
            log.warning("Schema change: new source column '%s' (%s). "
                        "Adding it to bronze.db_students.", column_name, column_type)
            con.execute(f'ALTER TABLE bronze.db_students ADD COLUMN "{column_name}" {column_type}')

    # 3. Insert BY NAME: columns are matched by their names, not their
    #    positions, so the order of columns no longer matters. Older rows
    #    simply have NULL in the new column.
    con.execute("""
        INSERT INTO bronze.db_students BY NAME
        SELECT *, now() AS _ingested_at,
               'ops.students' AS _source_file, ? AS _batch_id
        FROM ops.students
        WHERE updated_at > ?
    """, [batch_id, last])
    # -------------------------------------------------------------------------

    after = con.sql("SELECT count(*) FROM bronze.db_students").fetchone()[0]
    log.info("Inserted %s new rows into bronze.db_students (total now %s)",
             after - before, after)
    con.close()


if __name__ == "__main__":
    main()
