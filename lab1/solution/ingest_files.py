```python
"""
Lab 1, part 1: load the attendance CSV files into Bronze.

Run from the repository root:

    python lab1/solution/ingest_files.py

Every run replaces bronze.file_attendance with the current contents of
data/attendance/, so running it twice gives the same result (idempotent).
Rows that cannot be parsed are NOT loaded. DuckDB puts them in a table
called reject_errors instead, so we can see what went wrong.
"""

# ---------------------------------------------------------------------------
# Shared helpers used across the whole lab:
#   get_connection -> opens a DuckDB connection (configured in common.py)
#   get_logger     -> returns a logger tagged with a name (here "ingest_files")
#   new_batch_id   -> produces a fresh, unique identifier for this run so we
#                     can tell rows from one run apart from rows of another.
# ---------------------------------------------------------------------------
from common import get_connection, get_logger, new_batch_id

# Create a logger for this module. Every log line will be prefixed with
# "ingest_files", which makes it easy to filter the run's output.
log = get_logger("ingest_files")


def main():
    # ------------------------------------------------------------------
    # 1. Open a DuckDB connection and start a new batch.
    #    The batch_id is just a number (e.g. an int or a timestamp string)
    #    that uniquely identifies this invocation of the script. We stamp
    #    every row we load with it, so later stages can say "process only
    #    rows from batch N" if they need to.
    # ------------------------------------------------------------------
    con = get_connection()                 # connect to the DuckDB database
    batch_id = new_batch_id()              # generate a new run identifier
    log.info("Starting file load, batch %s", batch_id)

    # ------------------------------------------------------------------
    # 2. Make sure the "bronze" schema exists.
    #    In a medalion architecture the bronze layer holds raw data exactly
    #    as it arrived (plus a few helpful metadata columns). The schema is
    #    created once and reused on every subsequent run.
    # ------------------------------------------------------------------
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")

    # ------------------------------------------------------------------
    # 3. Read every CSV file under data/attendance/ in a single statement.
    #
    #    The clever part is DuckDB's read_csv():
    #
    #      filename = true
    #          Adds a virtual column called "filename" to every row, holding
    #          the path of the CSV file that row came from. We rename it to
    #          _source_file below so we never lose track of provenance.
    #
    #      store_rejects = true
    #          If a row can't be parsed (bad date, wrong number of columns,
    #          etc.) the script does NOT crash. Instead DuckDB writes the
    #          bad row into two temporary tables:
    #              reject_errors  -> what went wrong and where
    #              reject_scans   -> metadata about the file scan
    #          These tables live only for the current connection, so we
    #          must read them before calling con.close().
    #
    #      types = {'class_date': 'DATE'}
    #          Without this hint DuckDB infers column types by sampling
    #          the data. If even a single class_date value is malformed,
    #          DuckDB silently downgrades the WHOLE column to VARCHAR so
    #          it can still load every row. That would let bad dates
    #          sneak into bronze. By forcing DATE we tell DuckDB "treat
    #          this column as a date; if a value doesn't parse, reject
    #          the row instead of falling back to text."
    #
    #    We then wrap the read_csv() in a SELECT that adds three metadata
    #    columns so the bronze table is self-describing:
    #
    #       _source_file  -> the CSV file the row came from (renamed "filename")
    #       _ingested_at  -> the timestamp when the row entered bronze
    #       _batch_id     -> the run identifier (passed in as a parameter)
    #
    #    CREATE OR REPLACE TABLE means the bronze table is dropped and
    #    rebuilt on every run -> the script is idempotent (running it twice
    #    yields the exact same bronze.file_attendance table).
    #
    #    The "?" is a parameter placeholder; the actual batch_id value is
    #    supplied as the second argument to con.execute(...) below. Using
    #    a parameter (instead of string interpolation) is safer and lets
    #    DuckDB cache the prepared statement.
    # ------------------------------------------------------------------
    con.execute("""
        CREATE OR REPLACE TABLE bronze.file_attendance AS
        SELECT * EXCLUDE (filename),               -- keep all original columns
               filename      AS _source_file,      -- where the row came from
               now()         AS _ingested_at,      -- when we loaded it
               ?             AS _batch_id          -- which run loaded it
        FROM read_csv('data/attendance/*.csv',
                      filename = true,             -- track provenance
                      store_rejects = true,        -- quarantine bad rows
                      types = {'class_date': 'DATE'})  -- enforce strict typing
    """, [batch_id])

    # ------------------------------------------------------------------
    # 4. Report how many good rows made it into bronze.
    #    con.sql(...).fetchone() returns a one-row tuple; [0] grabs the
    #    scalar count out of it.
    # ------------------------------------------------------------------
    row_count = con.sql("SELECT count(*) FROM bronze.file_attendance").fetchone()[0]
    log.info("Loaded %s rows into bronze.file_attendance", row_count)

    # ------------------------------------------------------------------
    # 5. Inspect the rejected rows.
    #
    #    The reject_errors and reject_scans tables are TEMPORARY: they are
    #    scoped to this connection and disappear when we close it. So we
    #    must read them now, while the connection is still open.
    #
    #    We join reject_errors (the actual problem descriptions) with
    #    reject_scans (which file each scan_id/file_id refers to) so each
    #    rejected row tells a complete story:
    #
    #       file_path  -> which CSV file the bad line is in
    #       line       -> the 1-based line number inside that file
    #       error_type -> short description of the problem
    #       csv_line   -> the offending raw text (whitespace/newlines
    #                     trimmed so the log is easier to read)
    #
    #    Ordering by file_path and line makes the output deterministic
    #    and easy to scan.
    # ------------------------------------------------------------------
    rejects = con.sql("""
        SELECT s.file_path,
               e.line,
               e.error_type,
               trim(e.csv_line, chr(10) || chr(13) || ' ') AS csv_line
        FROM reject_errors e
        JOIN reject_scans s USING (scan_id, file_id)
        ORDER BY s.file_path, e.line
    """).fetchall()

    # First give a one-line summary, then walk through every rejected row
    # so the operator can see exactly what failed and why.
    log.info("%s rows rejected (see reject_errors)", len(rejects))
    for file_path, line, error_type, csv_line in rejects:
        log.warning("Rejected %s line %s (%s): %s",
                    file_path, line, error_type, csv_line)

    # ------------------------------------------------------------------
    # 6. Close the connection.
    #    Closing also drops the temporary reject_errors / reject_scans
    #    tables, which is fine because we've already logged everything we
    #    need from them. Bronze, however, is a persistent table and
    #    survives the close.
    # ------------------------------------------------------------------
    con.close()


# Standard Python idiom: only call main() when this file is run directly
# (e.g. `python lab1/solution/ingest_files.py`), not when it's imported
# as a module. That makes the file safe to import for testing too.
if __name__ == "__main__":
    main()
```