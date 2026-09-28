"""Scan the warehouse for readable NRIC-shaped values.

Run with:  make pii-check                       (default schemas)
           make pii-check schemas=bronze        (any schema list)

By default it looks in silver, gold, ref_silver and ref_gold (the schemas
where personal data is NOT supposed to be readable). Any of those that do
not exist yet are skipped, not treated as failures.

An NRIC-shaped value matches the pattern [STFGM][0-9]{7}[A-Z] as a whole
string. In this workshop the check letter is deliberately wrong (see
scripts/generate_data.py), so nothing here matches a real NRIC even if the
script flags it - the point is that the value is still readable and would
be a leak if the data were real.

Exit code: 0 if nothing was found, 1 if anything was.
"""

import argparse
import os
import sys
from pathlib import Path

import duckdb

DEFAULT_SCHEMAS = ["silver", "gold", "ref_silver", "ref_gold"]
NRIC_PATTERN = "[STFGM][0-9]{7}[A-Z]"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--schemas",
        help="Comma-separated list of schemas to scan. "
             f"Default: {','.join(DEFAULT_SCHEMAS)}",
    )
    return parser.parse_args()


def resolve_warehouse():
    path = os.environ.get("DUCKDB_PATH")
    if path:
        return Path(path)
    # Fallback: same location as the Day 1 loaders.
    root = Path(__file__).resolve().parent.parent
    return root / "warehouse" / "pipeline.duckdb"


def open_readonly(path):
    """Open the warehouse read-only. Give a plain-English error if it is locked."""
    try:
        return duckdb.connect(str(path), read_only=True)
    except duckdb.IOException as exc:
        message = str(exc).lower()
        if "lock" in message or "in use" in message:
            print("Database is in use. Close other DuckDB sessions and try again.",
                  file=sys.stderr)
            sys.exit(2)
        raise


def existing_schemas(con, requested):
    """Return only the schemas that actually exist in the warehouse."""
    have = {row[0] for row in con.execute(
        "SELECT schema_name FROM information_schema.schemata"
    ).fetchall()}
    kept = [s for s in requested if s in have]
    missing = [s for s in requested if s not in have]
    for s in missing:
        print(f"note: schema '{s}' does not exist (yet); skipped")
    return kept


def varchar_columns(con, schema):
    """Return (schema, table, column) tuples for every VARCHAR column in the schema."""
    return con.execute("""
        SELECT table_schema, table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = ?
          AND data_type ILIKE 'VARCHAR%'
        ORDER BY table_name, ordinal_position
    """, [schema]).fetchall()


def count_matches(con, schema, table, column):
    """Count NRIC-shaped values in one column."""
    return con.execute(
        f'''SELECT count(*) FROM "{schema}"."{table}"
            WHERE regexp_full_match("{column}", ?)''',
        [NRIC_PATTERN],
    ).fetchone()[0]


def main():
    args = parse_args()
    schemas = [s.strip() for s in args.schemas.split(",")] if args.schemas else list(DEFAULT_SCHEMAS)

    con = open_readonly(resolve_warehouse())
    schemas = existing_schemas(con, schemas)

    hits = []  # (schema.table.column, count)
    for schema in schemas:
        for s, t, col in varchar_columns(con, schema):
            n = count_matches(con, s, t, col)
            if n > 0:
                hits.append((f"{s}.{t}.{col}", n))

    con.close()

    if not hits:
        print("0 readable NRIC values found")
        sys.exit(0)

    for name, n in hits:
        print(f"{name}: {n} readable NRIC value(s)")
    sys.exit(1)


if __name__ == "__main__":
    main()
