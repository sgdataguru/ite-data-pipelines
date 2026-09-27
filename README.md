# ITE Data Pipelines Workshop

This repository is your workspace for the 3-day data pipelining workshop for ITE lecturers. You will build **ITE Student Analytics**, a small pipeline that brings together three sources (attendance CSV files, a student database and a grades API) into a DuckDB warehouse, using Python, SQL, dbt and Airflow. Everything runs inside GitHub Codespaces, so there is nothing to install on your own computer.

## Getting started

1. Click **Use this template** → **Create a new repository** (keep it under your own account).
2. In your new repository, click **Code** → **Codespaces** → **Create codespace on main**. Setup takes a few minutes the first time.
3. In the terminal, run:

   ```bash
   make api
   make check
   ```

   Every line should say `OK`. If a line says `FAIL`, run the fix it suggests, or ask a facilitator.

## Commands

| Command | What it does |
|---|---|
| `make check` | Checks tools, data and the mock API are ready |
| `make api` | Starts the mock grades API on port 8000 (log in `logs/api.log`) |
| `make api-stop` | Stops the mock grades API |
| `make init` | Creates the warehouse (`warehouse/pipeline.duckdb`) and empty Bronze tables |

Run the labs from the repository root, for example `python lab1/starter/ingest_files.py`.

## Folder guide

| Folder | Contents |
|---|---|
| `.devcontainer/` | Codespace setup: Python 3.12, tools and environment variables |
| `scripts/` | Helper scripts behind the `make` commands |
| `mock_api/` | The mock grades API and its synthetic data |
| `data/attendance/` | Attendance CSV files you load in Lab 1 |
| `data/fixtures/` | Files used by the facilitator's failure scenarios |
| `sources/` | The student database (SQLite) |
| `warehouse/` | Your DuckDB warehouse, created by `make init` |
| `logs/` | Pipeline and API logs |
| `lab1/` | Lab 1: files and database into Bronze (`starter/` and `solution/`) |
| `lab2/` | Lab 2: the grades API into Bronze (`starter/` and `solution/`) |
| `day1/` | Day 1 exercise: reviewing AI-generated code |
| `templates/` | Architecture, ingestion map, data contract and AI review templates |
| `journal.md` | Your teaching journal |

## Data and privacy

All data in this repository is synthetic. Never paste real student data or credentials into any AI tool.

## Tool versions

| Tool | Version |
|---|---|
| Python | 3.12 |
| DuckDB | 1.5.5 |
| dbt-core / dbt-duckdb | 1.11.15 / 1.11.0 |
| FastAPI / Uvicorn | 0.141.1 / 0.54.0 |
| requests / tenacity | 2.34.2 / 9.1.4 |
| pytest / ruff | 9.1.1 / 0.16.9 |
| Apache Airflow | 3.3.2 (separate environment at `/opt/airflow-venv`) |

## Facilitator

| Command | What it does |
|---|---|
| `make fail scenario=<x>` | Switches on a failure scenario: `a`, `b`, `c`, `e`, `ratelimit`, `auth`, or `off` to restore everything |
| `make reset` | Drops every Bronze table and recreates an empty `bronze.db_students` |
