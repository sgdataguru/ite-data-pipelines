"""Shared helpers for the lab scripts.

    get_connection()  opens the workshop warehouse (warehouse/pipeline.duckdb)
    new_batch_id()    returns a unique ID for one run of a pipeline
    get_logger()      logs to the console AND to logs/pipeline.log
"""

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

import duckdb

# The repository root (two folders up from this file).
ROOT = Path(__file__).resolve().parent.parent.parent

# Work from the repository root, so paths such as 'data/attendance/*.csv'
# work no matter which folder you run the script from.
os.chdir(ROOT)

WAREHOUSE = ROOT / "warehouse" / "pipeline.duckdb"
LOG_FILE = ROOT / "logs" / "pipeline.log"


def get_connection():
    """Open (or create) the DuckDB warehouse file."""
    WAREHOUSE.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(WAREHOUSE))


def new_batch_id():
    """A unique ID for this run, e.g. '20260915-093012-1a2b3c'.

    Every row loaded in the same run gets the same batch ID, so you can
    find (or delete) everything one run loaded.
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{uuid.uuid4().hex[:6]}"


def get_logger(name):
    """A logger that writes timestamped lines to the console and the log file."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:          # already set up (e.g. imported twice)
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    log_file = logging.FileHandler(LOG_FILE)
    log_file.setFormatter(formatter)
    logger.addHandler(log_file)
    return logger
