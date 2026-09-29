"""Run one SQL query against the workshop warehouse and print the result.

Run from the repository root:

    python scripts/query.py "SELECT count(*) FROM bronze.file_attendance"

The warehouse is opened read-only, so this can never change your data, and
it does not keep the file locked after it prints.
"""

import sys
from pathlib import Path

import duckdb

WAREHOUSE = Path(__file__).resolve().parent.parent / "warehouse" / "pipeline.duckdb"


def main():
    if len(sys.argv) != 2:
        print('Usage: python scripts/query.py "SELECT ... FROM ..."')
        sys.exit(1)
    if not WAREHOUSE.exists():
        print("No warehouse yet. Run: make init")
        sys.exit(1)
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    con.sql(sys.argv[1]).show(max_width=200)
    con.close()


if __name__ == "__main__":
    main()
