"""Lab 1, part 1: load the attendance CSV files into Bronze.

Run from the repository root:

    python lab1/starter/ingest_files.py

Your job: finish the TODOs below. Every run should replace
bronze.file_attendance with the current contents of data/attendance/.
Rows that cannot be parsed must NOT be loaded. DuckDB can put them in a
table called reject_errors instead, so we can see what went wrong.
"""

from common import get_connection, get_logger, new_batch_id

log = get_logger("ingest_files")


def main():
    con = get_connection()
    batch_id = new_batch_id()
    log.info("Starting file load, batch %s", batch_id)

    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")

    # TODO: Add the three metadata columns after "SELECT *":
    #   - the name of the file each row came from, called _source_file
    #     (hint: read_csv can add a "filename" column; rename it, and use
    #      EXCLUDE (filename) so it does not appear twice)
    #   - the time the row was loaded, called _ingested_at (hint: now())
    #   - the batch ID of this run, called _batch_id (hint: use ? and pass
    #     [batch_id] as the second argument of con.execute)
    #
    # TODO: Add options to read_csv:
    #   - filename = true       so you know which file each row came from
    #   - store_rejects = true  so bad rows go to reject_errors instead of
    #                           stopping the whole load
    #   - types = {'class_date': 'DATE'}  so a bad date is rejected, not
    #                           loaded as text
    con.execute("""
        CREATE OR REPLACE TABLE bronze.file_attendance AS
        SELECT *
        FROM read_csv('data/attendance/*.csv')
    """)

    row_count = con.sql("SELECT count(*) FROM bronze.file_attendance").fetchone()[0]
    log.info("Loaded %s rows into bronze.file_attendance", row_count)

    # reject_errors only lives for this connection, so read it now.
    # (This part only works once store_rejects = true is added above.)
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
