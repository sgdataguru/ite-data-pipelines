"""Lab 2: incremental load of the grades API into Bronze.

Start the mock API first, then run from the repository root:

    make api
    python lab2/solution/ingest_api.py

The script asks the API only for records changed since the last load (the
watermark), follows next_cursor from page to page, retries when the API is
busy or down (HTTP 429 or 5xx), and stops at once when the token is
rejected (HTTP 401).
"""

import logging
import os
import sys

import requests
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_delay,
    wait_exponential,
)

from common import get_connection, get_logger, new_batch_id

log = get_logger("ingest_api")

PAGE_SIZE = 500   # we ask for 500; the server may return fewer per page


class RetryableError(Exception):
    """An error worth retrying: the API is busy (429) or broken (5xx)."""


def log_retry(retry_state):
    """Called by tenacity before each wait, so every retry shows in the log."""
    error = retry_state.outcome.exception()
    wait = retry_state.next_action.sleep
    log.warning("Attempt %s failed (%s). Retrying in %.0f s.",
                retry_state.attempt_number, error, wait)


@retry(stop=stop_after_delay(120),                               # keep trying for up to 2 minutes
       wait=wait_exponential(multiplier=2, min=2, max=30),       # 2, 4, 8, 16, 30, 30 s
       retry=retry_if_exception_type(RetryableError),
       before_sleep=log_retry)
def get_page(url, params, token):
    r = requests.get(url, params=params, timeout=30,
                     headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 429 or r.status_code >= 500:
        raise RetryableError(f"{r.status_code} from {url}")
    r.raise_for_status()      # other 4xx errors: fail fast, no retry
    return r.json()


def extract_since(base_url, since):
    """Return every record changed after `since`, following next_cursor."""
    token = os.environ["SOURCE_API_TOKEN"]     # never type the token in the code
    url = f"{base_url}/records"
    params = {"updated_since": since, "limit": PAGE_SIZE}

    records = []
    page_number = 0
    while True:
        page = get_page(url, params, token)
        page_number += 1
        records.extend(page["data"])
        log.info("Page %s: %s records", page_number, len(page["data"]))

        if page["next_cursor"] is None:      # null means this was the last page
            break
        params["cursor"] = page["next_cursor"]
    return records


def get_watermark(con):
    """The newest updated_at already in Bronze, or the beginning of time."""
    table_exists = con.sql("""
        SELECT count(*) FROM information_schema.tables
        WHERE table_schema = 'bronze' AND table_name = 'api_grades'
    """).fetchone()[0]
    if not table_exists:
        return "1900-01-01T00:00:00"
    last = con.sql("""SELECT coalesce(max(updated_at), TIMESTAMP '1900-01-01')
                      FROM bronze.api_grades""").fetchone()[0]
    return last.isoformat()


def load(con, records, batch_id):
    """Insert the records into bronze.api_grades with the metadata columns."""
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    con.execute("""
        CREATE TABLE IF NOT EXISTS bronze.api_grades (
            record_id    INTEGER,
            student_id   VARCHAR,
            module_code  VARCHAR,
            assessment   VARCHAR,
            score        INTEGER,
            updated_at   TIMESTAMP,
            _ingested_at TIMESTAMP,
            _source_file VARCHAR,
            _batch_id    VARCHAR
        )
    """)
    rows = [
        (r["record_id"], r["student_id"], r["module_code"], r["assessment"],
         r["score"], r["updated_at"], "GET /records", batch_id)
        for r in records
    ]
    if rows:
        con.executemany("""
            INSERT INTO bronze.api_grades
            VALUES (?, ?, ?, ?, ?, ?, now(), ?, ?)
        """, rows)


def main():
    base_url = os.environ.get("MOCK_API_URL", "http://localhost:8000")
    if "SOURCE_API_TOKEN" not in os.environ:
        log.error("SOURCE_API_TOKEN is not set. Not calling the API.")
        sys.exit(1)

    con = get_connection()
    batch_id = new_batch_id()
    since = get_watermark(con)
    log.info("Starting API load, batch %s, records updated after %s", batch_id, since)

    try:
        records = extract_since(base_url, since)
    except requests.HTTPError as error:
        if error.response.status_code == 401:
            log.error("API rejected the token (401). Check SOURCE_API_TOKEN. Not retrying.")
        else:
            log.error("API returned %s. Not retrying.", error.response.status_code)
        sys.exit(1)
    except RetryError:
        log.error("API still failing after 2 minutes of retries. Giving up.")
        sys.exit(1)
    except requests.ConnectionError:
        log.error("Cannot reach the API at %s. Is it running? (make api)", base_url)
        sys.exit(1)

    load(con, records, batch_id)
    total = con.sql("SELECT count(*) FROM bronze.api_grades").fetchone()[0]
    log.info("Inserted %s new rows into bronze.api_grades (total now %s)", len(records), total)
    con.close()


if __name__ == "__main__":
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    main()
