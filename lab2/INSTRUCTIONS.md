# Lab 2: The Grades API into Bronze

**Time:** 35 minutes  |  **Work in:** `lab2/starter/ingest_api.py`  |  **Goal:** every grade, every page, only once

## The problem

The third source is the **grades API**: a small web service running inside
your Codespace on port 8000. You ask it for grade records over HTTP, the
same way a school system would ask a real vendor's API. Your job is to land
every grade record in `bronze.api_grades`.

Real APIs make that harder than reading a file, in four ways. Your script has
to handle each one.

| What the API does | What your script must do |
|---|---|
| Needs a **token** (a password for programs) | Read it from the environment variable `SOURCE_API_TOKEN`. Never type it into the code. |
| Returns at most **50 records per page**, plus a `next_cursor` bookmark | Keep asking for the next page until `next_cursor` is empty (`None`). |
| Sometimes says **"busy, slow down"** (HTTP 429) or **breaks for a while** (HTTP 500) | Wait and try again, a little longer each time. |
| Sometimes **rejects the token** (HTTP 401) | Stop at once with a clear message. Retrying cannot fix a bad token. |

The load is **incremental**, like the database in Lab 1. The script asks only
for records updated after the newest `updated_at` already in Bronze (the
watermark), so the second run fetches nothing new.

Start the API first, from the repository root:

```bash
make api
```

## What you write

Open `lab2/starter/ingest_api.py`. Everything except three pieces is already
written: the watermark, the loading into DuckDB and the error messages.
Finish the three TODOs.

### TODO 1: retry when the API is busy or down

Add a `@retry(...)` decorator (from the `tenacity` library) directly above
`def get_page(...)`, so that it:

- keeps trying for up to 2 minutes: `stop=stop_after_delay(120)`
- waits longer each time (2, 4, 8, 16, 30 seconds): `wait=wait_exponential(multiplier=2, min=2, max=30)`
- retries **only** on `RetryableError` (429 and 5xx): `retry=retry_if_exception_type(RetryableError)`
- logs every retry: `before_sleep=log_retry`

A 401 is not a `RetryableError`, so it is never retried.

### TODO 2: read the token

In `extract_since`, replace `token = ""` with the value of the environment
variable `SOURCE_API_TOKEN` (hint: `os.environ[...]`).

**Before you do this** the script stops with
`API rejected the token (401). Check SOURCE_API_TOKEN. Not retrying.`
That is your fail-fast message working.

### TODO 3: follow every page

Replace the single `get_page(...)` call with a loop:

1. Call `get_page(url, params, token)` and add `page["data"]` to `records`.
2. Log how many records the page had: `log.info("Page %s: %s records", page_number, len(page["data"]))`.
3. If `page["next_cursor"]` is `None`, that was the last page: stop.
4. Otherwise set `params["cursor"] = page["next_cursor"]` and go round again.

Watch out: a loop that never checks for `None` never ends. That is the same
defect as this morning's AI-generated sample.

Run it:

```bash
python lab2/starter/ingest_api.py
```

## The output you should get

The times and batch IDs will differ; the numbers must match.

**First run:** four pages of 50, 200 records.

```
INFO    ingest_api: Starting API load, batch 20261006-145210-7cbe0c, records updated after 1900-01-01T00:00:00
INFO    ingest_api: Page 1: 50 records
INFO    ingest_api: Page 2: 50 records
INFO    ingest_api: Page 3: 50 records
INFO    ingest_api: Page 4: 50 records
INFO    ingest_api: Inserted 200 new rows into bronze.api_grades (total now 200)
```

**Second run:** nothing new since the watermark.

```
INFO    ingest_api: Starting API load, batch 20261006-145302-3f81c2, records updated after 2026-09-25T12:09:52
INFO    ingest_api: Page 1: 0 records
INFO    ingest_api: Inserted 0 new rows into bronze.api_grades (total now 200)
```

Check what landed in the warehouse:

```bash
python scripts/query.py "SELECT count(*) AS row_count FROM bronze.api_grades"
python scripts/query.py "SELECT record_id, student_id, module_code, score, updated_at, _source_file FROM bronze.api_grades ORDER BY record_id LIMIT 3"
```

## You are done when

- [ ] `bronze.api_grades` has **200** rows, and the second run inserts **0**.
- [ ] The log shows **4 pages** on the first run.
- [ ] The token appears **nowhere** in your code: `grep -n "workshop-token" lab2/starter/ingest_api.py` prints nothing.
- [ ] (If the facilitator switches on a failure) a 429 or 500 shows `Attempt 1 failed ... Retrying in 2 s`, and a 401 stops at once.

## Checkpoint questions (the facilitator will ask)

1. How many rows are in `bronze.api_grades`?
2. Show me the line where the token is read.
3. Why do we retry a 429 but not a 401?

## If you are stuck

- `Cannot reach the API at http://localhost:8000`: run `make api`.
- The script never finishes: your loop is not stopping when `next_cursor` is `None`.
- `NameError` on `retry` or `stop_after_delay`: they are already imported at the top; check the spelling.
- Stuck for more than five minutes: ask your neighbour, then the facilitator.
