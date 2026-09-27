"""Facilitator: drop every Bronze table and start again from a clean state.

Run with:  make reset

Drops all tables in the "bronze" schema, then runs the same steps as
make init, so bronze.db_students exists again and is empty.
"""

import duckdb

from init_db import ROOT, WAREHOUSE, init_bronze


def main():
    WAREHOUSE.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(WAREHOUSE))

    tables = con.sql("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'bronze'
    """).fetchall()
    for (table_name,) in tables:
        con.execute(f'DROP TABLE bronze."{table_name}"')
        print(f"Dropped bronze.{table_name}")

    init_bronze(con)
    con.close()
    print(f"Reset complete: {WAREHOUSE.relative_to(ROOT)} has an empty bronze.db_students")


if __name__ == "__main__":
    main()
