# Lab 1: Files and Database into Bronze

**Time:** 35 minutes  |  **Work in:** `lab1/starter/`  |  **Goal:** two Bronze tables, no lost rows

## The problem

ITE Student Analytics needs its raw data in one place: the DuckDB warehouse
(`warehouse/pipeline.duckdb`). This lab brings in two of the three sources.

| Source | Where it is | What arrives | Goes into |
|---|---|---|---|
| Attendance | `data/attendance/*.csv` (5 daily CSV files) | One row per student, class date and module | `bronze.file_attendance` |
| Student records | `sources/ops.db` (a SQLite database, table `students`) | One row per student; rows change over time | `bronze.db_students` |

**Bronze** is the raw landing layer. We copy the data in as it is, and we
never lose a row. Two of the attendance rows are broken on purpose. They
must not crash the load, and they must not disappear: they are set aside
(quarantined) so a person can look at them.

Every Bronze table carries three extra columns, so anyone can trace a row
back to where it came from:

| Column | Meaning | Example |
|---|---|---|
| `_ingested_at` | When the row was loaded | `2026-10-06 13:52:10` |
| `_source_file` | Where the row came from | `data/attendance/attendance_2026-09-07.csv` or `ops.students` |
| `_batch_id` | Which run loaded it | `20261006-135210-1a2b3c` |

Both loads must be **idempotent**: running the same script twice gives the
same result, never duplicates.

## What you write

You do **not** start from an empty file. Each starter file already runs from
top to bottom; your job is to finish the lines marked `# TODO`. Read the
comment above each TODO: it tells you exactly what to add.

### Part 1: `lab1/starter/ingest_files.py` (about 15 minutes)

The script replaces `bronze.file_attendance` with everything in
`data/attendance/` on every run. That is what makes it idempotent.

1. Add three options to `read_csv(...)`:
   - `filename = true`: DuckDB adds a column saying which file each row came from.
   - `store_rejects = true`: bad rows go to a side table called `reject_errors` instead of stopping the load.
   - `types = {'class_date': 'DATE'}`: a date such as `2026-13-45` is rejected, not quietly loaded as text.
2. Add the three metadata columns after `SELECT *`:
   `_source_file` (the renamed `filename` column), `_ingested_at` (`now()`) and
   `_batch_id` (use `?` and pass `[batch_id]`). Use `SELECT * EXCLUDE (filename)`
   so the file name does not appear twice.

Run it from the repository root:

```bash
python lab1/starter/ingest_files.py
```

**Before you finish the TODOs** you will see
`Invalid Input Error: Schema mismatch between globbed files`. That is the
broken row with an extra column stopping the whole load. `store_rejects = true`
is the fix.

### Part 2: `lab1/starter/ingest_database.py` (about 15 minutes)

This is an **incremental** load: only rows changed since the last load are
copied. "Since the last load" is the **watermark**: the newest `updated_at`
value already in Bronze.

1. Replace `last = None` with a query that returns the watermark:
   the newest `updated_at` in `bronze.db_students`, or `TIMESTAMP '1900-01-01'`
   if the table is empty (use `coalesce(max(updated_at), ...)`).
2. Add the three metadata columns after `SELECT *`, in this order:
   `now() AS _ingested_at, 'ops.students' AS _source_file, ? AS _batch_id`.
   Then pass `[batch_id, last]` instead of `[last]`: one value per `?`, in order.

Run it:

```bash
make init            # only needed once: creates the empty bronze.db_students
python lab1/starter/ingest_database.py
```

**Before you finish the TODOs** you will see
`Binder Error: table db_students has 11 columns but 8 values were supplied`.
Bronze has three metadata columns that the SELECT does not provide yet.

## The output you should get

Run each script **twice**. The dates, times and batch IDs will differ; the
numbers must match.

**Part 1, both runs:**

```
INFO    ingest_files: Starting file load, batch 20261006-135210-1a2b3c
INFO    ingest_files: Loaded 404 rows into bronze.file_attendance
INFO    ingest_files: 2 rows rejected (see reject_errors)
WARNING ingest_files: Rejected data/attendance/attendance_2026-09-08.csv line 47 (TOO MANY COLUMNS): S0012,2026-09-08,IT102,PRESENT,extra
WARNING ingest_files: Rejected data/attendance/attendance_2026-09-10.csv line 37 (CAST): S0021,2026-13-45,DE102,PRESENT
```

**Part 2, first run:**

```
INFO    ingest_database: Watermark (newest updated_at in Bronze): 1900-01-01 00:00:00
INFO    ingest_database: Inserted 40 new rows into bronze.db_students (total now 40)
```

**Part 2, second run:**

```
INFO    ingest_database: Watermark (newest updated_at in Bronze): 2026-09-25 12:17:04
INFO    ingest_database: Inserted 0 new rows into bronze.db_students (total now 40)
```

Check what landed in the warehouse:

```bash
python scripts/query.py "SELECT count(*) AS row_count FROM bronze.file_attendance"
python scripts/query.py "SELECT student_id, full_name, _ingested_at, _source_file, _batch_id FROM bronze.db_students LIMIT 3"
```

## You are done when

- [ ] `bronze.file_attendance` has **404** rows, and running Part 1 again still gives 404.
- [ ] The log names the **2** rejected rows, with file, line and reason.
- [ ] `bronze.db_students` has **40** rows; the second run inserts **0**.
- [ ] Both tables have `_ingested_at`, `_source_file` and `_batch_id` filled in.

## Checkpoint questions (the facilitator will ask)

1. How many rows in each Bronze table, and how many were quarantined?
2. Why does the second database run insert nothing?
3. Why do we keep the rejected rows instead of deleting them?

## If you are stuck

- Run every command from the repository root: the prompt should end in `ite-data-pipelines (main) $`.
- `bronze.db_students does not exist`: run `make init`.
- Read the error's last line first. It usually names the column or value at fault.
- Stuck for more than five minutes: ask your neighbour, then the facilitator.
