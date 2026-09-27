"""Lab 1, part 1: load the attendance CSV files into Bronze.

Run from the repository root:

    python lab1/solution/ingest_files.py

Every run replaces bronze.file_attendance with the current contents of
data/attendance/, so running it twice gives the same result (idempotent).
Rows that cannot be parsed are NOT loaded. DuckDB puts them in a table
called reject_errors instead, so we can see what went wrong.
"""

from common import get_connection, get_logger, new_batch_id

log = get_logger("ingest_files")


def main():
    con = get_connection()
    batch_id = new_batch_id()
    log.info("Starting file load, batch %s", batch_id)

    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")

    # Load every CSV file in the folder in one go.
    #   filename = true       adds a column with the file each row came from
    #   store_rejects = true  bad rows go to reject_errors instead of failing
    #   types = ...           class_date must be a DATE. Without this hint,
    #                         DuckDB sees one bad date and reads the whole
    #                         column as text, so the bad row slips through.
    # We then add three metadata columns: where the row came from, when it
    # was loaded, and which run loaded it.
    con.execute("""
        CREATE OR REPLACE TABLE bronze.file_attendance AS
        SELECT * EXCLUDE (filename),
               filename      AS _source_file,
               now()         AS _ingested_at,
               ?             AS _batch_id
        FROM read_csv('data/attendance/*.csv',
                      filename = true, store_rejects = true,
                      types = {'class_date': 'DATE'})
    """, [batch_id])

    row_count = con.sql("SELECT count(*) FROM bronze.file_attendance").fetchone()[0]
    log.info("Loaded %s rows into bronze.file_attendance", row_count)

    # reject_errors only lives for this connection, so read it now.
    rejects = con.sql("""
        SELECT s.file_path, e.line, e.error_type, trim(e.csv_line, chr(10) || chr(13) || ' ') AS csv_line
        FROM reject_errors e
        JOIN reject_scans s USING (scan_id, file_id)
        ORDER BY s.file_path, e.line
    """).fetchall()
    log.info("%s rows rejected (see reject_errors)", len(rejects))
    for file_path, line, error_type, csv_line in rejects:
        log.warning("Rejected %s line %s (%s): %s", file_path, line, error_type, csv_line)

    con.close()


if __name__ == "__main__":
    main()
