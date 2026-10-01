# ITE Data Pipelines Workshop

This repository is your workspace for the 3-day data pipelining workshop for ITE lecturers. You will build **ITE Student Analytics**, a small pipeline that brings together three sources (attendance CSV files, a student database and a grades API) into a DuckDB warehouse, using Python, SQL, dbt and Airflow. Everything runs inside GitHub Codespaces, so there is nothing to install on your own computer.

## Getting started

1. Click **Use this template** → **Create a new repository** (keep it under your own account).
   Keep the repository name `ite-data-pipelines` when you create your copy.
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
| `make bronze` | Day 2: populates Bronze by running the three Day 1 loaders |
| `make pii-check` | Day 2: scans Silver/Gold for readable NRIC-shaped values (add `schemas=<list>` to check elsewhere) |
| `make update` | Brings the latest workshop files from the facilitators' template into your copy |
| `make airflow` | Day 3: starts Airflow on port 8080 (log in `logs/airflow.log`) |
| `make airflow-stop` | Day 3: stops Airflow |
| `make dag-test` | Day 3: checks every DAG in `dags/` loads without errors |

Run the labs from the repository root, for example `python lab1/starter/ingest_files.py`.

## Day 2

Day 2 layers dbt and a small AI enrichment step on top of the Bronze
tables. Two dbt projects sit side by side:

- `dbt/` - the project you build in.
- `dbt/reference/` - the completed answers, in a separate project so your
  model names never clash. Materialises into `ref_silver` / `ref_gold`.

Both projects share the same warehouse (`warehouse/pipeline.duckdb`) and
the same profile (`ite_pipelines`).

To browse the model catalog and lineage in the browser:

```bash
cd dbt && dbt docs generate && dbt docs serve --port 8081
```

The Codespace forwards port 8081 automatically.

## Getting the latest workshop files

Your repository is a copy of the template, so `git pull` only fetches from
your own copy and never sees new workshop files. Use `make update` instead.
It replaces the facilitator files (scripts, reference answers, templates,
exercises), adds new starter files you do not have yet, and never touches
your own work (`dbt/models/`, `dbt/tests/`, `lab1/`, `lab2/`, `journal.md`).

The first time, your Makefile does not have `update` yet. Paste this instead:

```bash
curl -fsSL https://raw.githubusercontent.com/sgdataguru/ite-data-pipelines/main/scripts/update_from_template.sh | bash
```

Then review the changes and commit them:

```bash
git status
git commit -am "Sync workshop files"
```

## Day 3

Day 3 runs the whole pipeline on a schedule with Airflow, adds alerts and a
run audit, and checks every change automatically before it is merged.

**Start here:** [`day3/CHEATSHEET.md`](day3/CHEATSHEET.md) explains every Airflow
command in plain words, block by block, plus how to make the Codespace fast.
The hello-world DAG for Blocks 2 and 3 is `templates/airflow_hello.py`.

```bash
make api            # the grades API must be running for ingest_api
make airflow        # start Airflow (can take a minute or two the first time)
make dag-test       # check every DAG loads
make airflow-stop   # stop Airflow at the end of the day
```

To open the Airflow UI: open the **Ports** tab, find port **8080**
("Airflow UI") and click the globe icon. No login is needed.

Two DAGs are in `dags/`:

- `reference_pipeline` is the complete example: three loads, then
  `dbt build` on `dbt/reference`, then a row in `audit.pipeline_runs`. It is
  **paused** until you unpause it in the UI. Unpausing starts one run
  straight away.
- `capstone_pipeline` is yours. Only `ingest_files` is finished; the
  `# TODO` blocks tell you what to add.

Alerts are written to `logs/alerts.log` (one line per retry or failure). Each
run's row counts and dbt results are in `audit.pipeline_runs`.

**CI on pull requests.** `.github/workflows/pipeline-ci.yml` runs two checks
on every pull request to `main`. The first installs the tools, runs `ruff`,
loads the three sources into a fresh warehouse and runs `dbt seed` and
`dbt build` on your `dbt/` project, so a model change that breaks a test
turns the pull request red. The second installs Airflow and checks that
every DAG in `dags/` loads. Both appear at the bottom of the pull-request
page.

## Folder guide

| Folder | Contents |
|---|---|
| `.devcontainer/` | Codespace setup: Python 3.12, tools and environment variables |
| `scripts/` | Helper scripts behind the `make` commands |
| `mock_api/` | The mock grades API and its synthetic data |
| `data/attendance/` | Attendance CSV files you load in Lab 1 |
| `data/feedback/` | Day 2: student feedback comments for the AI enrichment lab |
| `data/fixtures/` | Files used by the facilitator's failure scenarios |
| `sources/` | The student database (SQLite) |
| `warehouse/` | Your DuckDB warehouse, created by `make init` |
| `logs/` | Pipeline and API logs |
| `lab1/` | Lab 1: files and database into Bronze (`starter/` and `solution/`) |
| `lab2/` | Lab 2: the grades API into Bronze (`starter/` and `solution/`) |
| `dbt/` | Day 2: your dbt project (Silver and Gold models) |
| `dbt/reference/` | Day 2: the reference dbt project (facilitator answers) |
| `enrich/` | Day 2: the AI enrichment lab (redaction, classifier, review sample) |
| `dags/` | Day 3: Airflow DAGs (`reference_pipeline`, your `capstone_pipeline`) and the alert callbacks |
| `tests/` | Day 3: the DAG integrity test run by `make dag-test` and CI |
| `.github/workflows/` | Day 3: the CI checks that run on every pull request |
| `day1/` | Day 1 exercise: reviewing AI-generated code |
| `day2/` | Day 2 exercise: the governance audit PDF |
| `day3/` | Day 3 exercise: incident logs to diagnose |
| `templates/` | Architecture, ingestion map, data contract, AI review, star schema, production readiness, runbook and lesson plan templates |
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
| Apache Airflow | 3.3.2 (separate environment at `/opt/airflow-venv`, with pytest 9.1.1) |

## Facilitator

| Command | What it does |
|---|---|
| `make fail scenario=<x>` | Switches on a failure scenario: `a`, `b`, `c`, `dq`, `e`, `ratelimit`, `auth`, or `off` to restore everything |
| `make reset` | Drops every Bronze table and recreates an empty `bronze.db_students` |
| `make dbt-reference` | Day 2: builds the reference dbt project (`dbt/reference/`) |
