"""Mock grades API for the ITE data pipelines workshop.

Start it with:  make api        (stop it with: make api-stop)

It serves the synthetic records in grades_seed.json. The facilitator can make
it misbehave with "make fail scenario=<x>", which writes mock_api/state.json.
This app reads state.json on EVERY request, so a new mode takes effect
immediately, without restarting the server.

Endpoints:
    GET /health    no login needed
    GET /records   needs the header  Authorization: Bearer <SOURCE_API_TOKEN>
"""

import base64
import json
import os
import time
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Header, Query
from fastapi.responses import JSONResponse

HERE = Path(__file__).resolve().parent
SEED_FILE = HERE / "grades_seed.json"
STATE_FILE = HERE / "state.json"

MAX_PAGE_SIZE = 50        # the server never returns more than 50 records a page
OUTAGE_SECONDS = 30       # how long mode "a" keeps returning HTTP 500

app = FastAPI(title="ITE mock grades API")

# Load the records once and sort them the way the API promises:
# by updated_at, then record_id.
RECORDS = json.loads(SEED_FILE.read_text())
RECORDS.sort(key=lambda r: (r["updated_at"], r["record_id"]))

# Counts /records requests since the current mode was set.
# Used by the "ratelimit" mode.
request_counter = 0
counter_mode_set_at = None


def read_state():
    """Return the current failure mode settings, e.g. {"mode": "off"}."""
    try:
        return json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"mode": "off"}


def error(status_code, message, headers=None):
    return JSONResponse(status_code=status_code, content={"error": message}, headers=headers)


def encode_cursor(position):
    """The cursor is 'opaque': clients just send it back. Inside, it is a position."""
    return base64.urlsafe_b64encode(str(position).encode()).decode()


def decode_cursor(cursor):
    return int(base64.urlsafe_b64decode(cursor.encode()).decode())


@app.get("/health")
def health():
    return {"status": "ok", "mode": read_state().get("mode", "off")}


@app.get("/records")
def records(
    authorization: str | None = Header(default=None),
    updated_since: str | None = None,
    limit: int = Query(default=500, ge=1, le=500),
    cursor: str | None = None,
):
    global request_counter, counter_mode_set_at
    state = read_state()
    mode = state.get("mode", "off")

    # Start counting again from 1 whenever a new mode is set.
    if state.get("set_at") != counter_mode_set_at:
        counter_mode_set_at = state.get("set_at")
        request_counter = 0
    request_counter += 1

    # 1. Check the token.
    expected = "Bearer " + os.environ.get("SOURCE_API_TOKEN", "")
    if authorization != expected:
        return error(401, "Invalid or missing token")

    # 2. Failure modes set by "make fail scenario=<x>".
    if mode in ("auth", "e"):
        return error(401, "Token expired")
    if mode == "a":
        seconds_since_set = time.time() - state.get("set_at", 0)
        if seconds_since_set < OUTAGE_SECONDS:
            return error(500, "Internal server error (simulated outage)")
    if mode == "ratelimit" and request_counter % 3 != 0:
        # Two out of every three requests are refused: the 1st and 2nd are
        # refused, the 3rd succeeds, and so on.
        return error(429, "Too many requests", headers={"Retry-After": "2"})

    # 3. Filter by updated_since (strictly greater than).
    rows = RECORDS
    if updated_since:
        try:
            since = datetime.fromisoformat(updated_since)
        except ValueError:
            return error(400, "updated_since must be an ISO timestamp")
        rows = [r for r in rows if datetime.fromisoformat(r["updated_at"]) > since]

    # 4. Paginate. The cursor says where the next page starts.
    try:
        start = decode_cursor(cursor) if cursor else 0
    except ValueError:
        return error(400, "Invalid cursor")
    page_size = min(limit, MAX_PAGE_SIZE)
    page = rows[start:start + page_size]
    end = start + page_size
    next_cursor = encode_cursor(end) if end < len(rows) else None

    return {"data": page, "next_cursor": next_cursor}
