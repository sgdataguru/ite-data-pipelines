"""Alert callbacks shared by the workshop DAGs.

There is no DAG in this file. Airflow reads every Python file in dags/, but
a file that does not create a DAG is simply ignored, so helper modules like
this one can live next to the DAGs that import them.

How the DAGs use it:

    from pipeline_alerts import on_failure, on_retry

    default_args = {
        "on_retry_callback": on_retry,      # each failed try that WILL be retried
        "on_failure_callback": on_failure,  # only after the LAST try has failed
    }

Each alert adds one line to logs/alerts.log, for example:

    2026-09-30 14:03:22 SGT | RETRYING | reference_pipeline.ingest_api | try 1

If the environment variable ALERT_WEBHOOK_URL is set (for example a Teams or
Slack incoming webhook), the same line is also POSTed there as {"text": ...}.
"""

import json
import logging
import os
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# The repository root is one folder up from dags/.
REPO = Path(__file__).resolve().parents[1]
ALERT_LOG = REPO / "logs" / "alerts.log"
SGT = ZoneInfo("Asia/Singapore")

log = logging.getLogger(__name__)


def _alert(status, context):
    """Write one alert line to logs/alerts.log and, if configured, the webhook."""
    ti = context["ti"]
    # try_number counts from 1: "try 1" is the first attempt.
    line = (f"{datetime.now(SGT):%Y-%m-%d %H:%M:%S} SGT | {status} | "
            f"{ti.dag_id}.{ti.task_id} | try {ti.try_number}")

    ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ALERT_LOG.open("a") as f:
        f.write(line + "\n")

    webhook = os.environ.get("ALERT_WEBHOOK_URL")
    if webhook:
        try:
            request = urllib.request.Request(
                webhook,
                data=json.dumps({"text": line}).encode(),
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(request, timeout=5)
        except Exception as error:      # an alert must never crash the task
            log.warning("Could not post alert to ALERT_WEBHOOK_URL: %s", error)


def on_retry(context):
    """Called by Airflow after a failed try that will be retried."""
    _alert("RETRYING", context)


def on_failure(context):
    """Called by Airflow after the last try has failed."""
    _alert("FAILED", context)
