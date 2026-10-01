# Day 3 Cheat Sheet: for lecturers

Day 3 is about **orchestration**. Day 1 built the loaders, Day 2 built the
transformations. Today they get stitched together, scheduled and watched.

The tool is **Airflow**. The idea is simple: write Python that says "run this,
then this, then this", and let Airflow handle the when, the retries and the
log keeping.

Nothing here needs prior Airflow knowledge. Every command is explained in
plain words. If a line is marked ⚙️ [ADVANCED: can skip], don't worry about
it on your first run.

Run every command from the repository root. Your prompt should end in
`ite-data-pipelines (main) $`.

---

## Before you start: make the Codespace fast

Airflow is the heaviest thing we run all week. Five minutes of setup saves
waiting all day.

| # | Step | Why |
|---|---|---|
| 1 | **Reuse the Codespace you used on Day 1 and 2.** Start it from **Code → Codespaces**, don't create a new one. | A new Codespace re-installs everything (several minutes). A restarted one is ready in about a minute. |
| 2 | **Switch to a 4-core machine for today.** Codespaces list (github.com/codespaces) → **⋯** next to yours → **Change machine type** → **4-core** → restart. Your files are kept. | Airflow runs a scheduler, a web server and a DAG processor at the same time. 2-core works, 4-core is noticeably snappier. |
| 3 | **Get the latest files** and load the settings: `make update`, then `source scripts/workshop_env.sh`. | Brings in today's DAGs and this sheet; sets the paths Airflow and dbt need. New terminals pick them up automatically. |
| 4 | **Run only what you need.** One `make airflow` per Codespace; `make airflow-stop` and `make api-stop` when you finish. Close terminals you no longer use. | Every extra process takes memory from Airflow. |
| 5 | **Stop the Codespace at the end of the day** (Codespaces menu → **Stop Current Codespace**). Don't delete it. | A running Codespace uses your free hours; a deleted one has to be rebuilt. |

After a Codespace restarts (or sleeps after 30 idle minutes), background
programs stop. Run `make api` and `make airflow` again.

---

## Part A: the Airflow vocabulary

Airflow is three things at once:

1. A **scheduler** that decides when things run.
2. A **web UI** on port 8080 where you watch them run.
3. A **library** you import in Python to describe what should happen.

### How Airflow is laid out in this repository

| Word | What it means here |
|---|---|
| **`AIRFLOW_HOME`** | The folder Airflow keeps its own files in: `.airflow/` at the repository root. |
| **DAG** | A Python file that describes a pipeline. Ours live in **`dags/`** at the repository root. |
| **Task** | One step inside a DAG: "load files", "load database", "build dbt". |
| **Operator** | The kind of task. `PythonOperator` runs Python; `BashOperator` runs a shell command; `EmptyOperator` does nothing (a placeholder). Our DAGs use `@task.bash`, the decorator form of `BashOperator`. |
| **Run** | One execution of a DAG, for one scheduled moment (ours: 06:00 every day). |
| **Metadata database** | A small SQLite file where Airflow remembers every run: `.airflow/airflow.db`. |
| **Pool** | A limit on how many tasks run at once. Our `duckdb` pool has 1 slot, because DuckDB allows one writer at a time. |

| What | Where |
|---|---|
| DAG files | `dags/` (`reference_pipeline.py`, `capstone_pipeline.py`, `pipeline_alerts.py`) |
| Task logs | `.airflow/logs/` |
| Airflow's own log | `logs/airflow.log` |
| Alerts | `logs/alerts.log` |
| Run audit | table `audit.pipeline_runs` in the warehouse |

Edit a DAG file and save it: Airflow notices within about 30 seconds. No restart needed.

### The commands you will see all day

**`make airflow`** ✅
What it does: starts Airflow in the background (it runs `airflow standalone`,
which is the scheduler + web UI + DAG processor + metadata database in one),
waits until it is healthy, and creates the `duckdb` pool. It also tells Airflow
where the main Python and dbt are, so the tasks can run the lab scripts.
Success looks like: `Airflow is ready on port 8080.`
Why not type `airflow standalone` yourself? It would miss those settings, and
the tasks would fail with "MAIN_PYTHON is not set".

**`make airflow-stop`** ✅
What it does: stops the Airflow that `make airflow` started, and nothing else.

**`source /opt/airflow-venv/bin/activate`**
What it does: switches this terminal to the Airflow Python, so you can type
`airflow ...` commands. Airflow lives in its own environment, separate from
dbt. `deactivate` switches back.

**`airflow dags list`**
What it does: prints every DAG Airflow has found.
When to use it: to check Airflow has noticed a new DAG file.
Success looks like: your DAG name in the list. If it is missing, run
`airflow dags list-import-errors`: it shows the file and line with the mistake.
(`make dag-test` does the same check without Airflow running.)

**`airflow dags trigger <dag_id>`**
What it does: runs the DAG now, outside its schedule. Same as the ▶ button in the UI.
Success looks like: a new column in the UI's Grid view within a few seconds.
The DAG must be unpaused to actually run.

**`airflow dags test <dag_id>`**
What it does: runs the whole DAG once, right here in the terminal, without
the scheduler. You see every task's output scroll past.
When to use it: trying a DAG before you switch on its schedule.
Note: the run is still recorded (you will see it in the UI). If a task fails,
the command waits through the retries, so press Ctrl+C rather than wait.

**`airflow tasks test <dag_id> <task_id>`**
What it does: runs one task on its own, ignoring the tasks before it.
When to use it: one broken step, and you want to retry just that step.

**`airflow dags pause <dag_id>` / `airflow dags unpause <dag_id>`**
What it does: stops / starts the schedule for one DAG, without deleting it.
UI equivalent: the toggle next to the DAG name. Unpausing starts one run straight away.

**`airflow backfill create --dag-id <dag_id> --from-date <date> --to-date <date>`**
What it does: creates a run for every scheduled moment in a date range.
When to use it: yesterday's run failed and you need to catch up, or a new DAG
needs history. The DAG must be **unpaused**, otherwise the runs wait in "queued".
(In older Airflow this was `airflow dags backfill`; Airflow 3 renamed it.)

⚙️ [ADVANCED: can skip] `airflow variables`, `airflow connections`, `airflow pools list`
Storing settings, credentials and concurrency limits inside Airflow.
Important in production; today the token comes from an environment variable,
and `make airflow` creates the one pool we need.

### The UI you'll be teaching from (port 8080)

Open the **Ports** tab, find **8080** ("Airflow UI") and click the globe icon.
No login is needed.

- **DAGs**: the list. Toggle on/off, click a name to open it.
- **Grid**: one column per run, one row per task; each square is coloured by its state.
- **Graph**: the DAG drawn as boxes and arrows.
- **Logs**: click a square in Grid, then **Logs**. Everything the task printed is there.
- **States**: green = success, red = failed, yellow = up for retry, orange = upstream failed (never ran because an earlier task failed). Hover any square to see its state in words.

---

## Part B: block-by-block commands

Each command is marked:

- ✅ [MUST RUN]: the workshop breaks without this
- 🟡 [OPTIONAL]: nice to show, doesn't affect the rest
- ⚙️ [ADVANCED: can skip]: powerful but confusing for first-timers

### Before anything

```bash
make update
source scripts/workshop_env.sh
git commit -am "Sync workshop files"
```

✅ [MUST RUN]: today's files and settings.

```bash
make api
make bronze
make check
```

✅ [MUST RUN]: the grades API, full Bronze tables, every line OK.
The Airflow line says `INFO Airflow not running`; that is expected until the next step.

### Block 1: Start Airflow and tour the UI

```bash
make airflow
```

✅ [MUST RUN]: about 20 to 30 seconds. Then open port 8080.

What to point at in the UI:

- The DAGs list shows two DAGs: `reference_pipeline` (the complete example)
  and `capstone_pipeline` (yours). Both are **paused**.
- Click `reference_pipeline` → **Graph**: three loads, then `dbt_build`, then `record_run`.
- Toggle it **on**, then press ▶ **Trigger**. Watch the squares turn green in **Grid**.
  Click one → **Logs**: it is the same output as Day 1.

```bash
make dag-test
```

🟡 [OPTIONAL]: checks every DAG file loads. Expect `2 passed`.

### Block 2: DAG anatomy with a hello-world DAG

```bash
cp templates/airflow_hello.py dags/hello.py
code dags/hello.py
```

✅ [MUST RUN]: copies the smallest possible DAG into the DAGs folder and opens it.
Read it top to bottom: the imports, `with DAG(...)`, three tasks, and the line
`start >> say_hello >> show_date` that sets the order.

Wait about 30 seconds, then:

```bash
source /opt/airflow-venv/bin/activate
airflow dags list
```

✅ [MUST RUN]: `hello` should be in the list.

```bash
airflow dags test hello
```

✅ [MUST RUN]: runs it in the terminal. Look for `Hello from Airflow!` and `Bash says hi`.
Then find `hello` in the UI and open its **Graph** and **Logs**.

### Block 3: Operators and the task tree

Point at the three operators in `dags/hello.py`:

1. `EmptyOperator`: a placeholder, useful for structure.
2. `PythonOperator`: calls a Python function (`greet`).
3. `BashOperator`: runs a shell command. This is how our pipeline runs the lab
   scripts and `dbt build`; `@task.bash` in `reference_pipeline.py` is the same
   thing written as a decorator.

Change the order or add a task, save, and run `airflow dags test hello` again.
The **Graph** view should match the `>>` line.

⚙️ [ADVANCED: can skip] `BranchPythonOperator` for "if this, then that" paths.

### Block 4: Orchestrate the three loaders (your capstone DAG)

```bash
code dags/capstone_pipeline.py
```

✅ [MUST RUN]: the main lab of the day. `ingest_files` is already done.
Work through the `# TODO` blocks from the top:

1. `ingest_database`: runs `lab1/solution/ingest_database.py`
2. `ingest_api`: runs `lab2/solution/ingest_api.py`
3. the dependency line: the three loads first
4. `default_args`: 3 retries, 1 minute apart, a 20-minute timeout, the `duckdb` pool, the two alert callbacks

`dags/reference_pipeline.py` is the worked answer to compare with.

After each change:

```bash
make dag-test
```

✅ [MUST RUN]: your file still loads.

Test one task on its own:

```bash
airflow tasks test capstone_pipeline ingest_files
```

✅ [MUST RUN]: should end with `Loaded 404 rows` and `2 rows rejected`, the Day 1 output.

Test the whole DAG:

```bash
airflow dags test capstone_pipeline
```

✅ [MUST RUN]: every task in order, in the terminal.
Then unpause `capstone_pipeline` in the UI, trigger it, and watch it go green.

### Block 5: Add dbt, then watch it handle a failure

Add the last two TODOs to `dags/capstone_pipeline.py`: `dbt_build` (runs
`dbt build` in `dbt/`) and `record_run`. Save, `make dag-test`, trigger it.
✅ [MUST RUN]: expect all green.

Now break it on purpose:

```bash
make fail scenario=auth
```

✅ [MUST RUN]: the mock API now rejects the token with HTTP 401.

Trigger `reference_pipeline` (or your capstone) again, then:

```bash
cat logs/alerts.log
```

✅ [MUST RUN]: a `RETRYING` line appears within seconds.

Point at the UI:

- The yellow square on `ingest_api` (up for retry), then red if you wait.
- Click it → **Logs** → `API rejected the token (401)`.
- `dbt_build` and `record_run` are **upstream failed**: they never ran.

Fix it:

```bash
make fail scenario=off
```

✅ [MUST RUN]: the next retry (about a minute later) succeeds, and the rest of the run goes green.
If the task already went red: click it in Grid → **Clear task**, and Airflow runs it again.

The teaching moment that lands: the pipeline recovered without anyone touching code.
That is what orchestration buys you.

### Block 6: Monitoring, backfills and who to call

What happened, run by run:

```bash
python scripts/query.py "SELECT run_id, rows_file_attendance, dbt_pass, dbt_warn, dbt_error FROM audit.pipeline_runs ORDER BY recorded_at DESC LIMIT 5"
```

✅ [MUST RUN]: one row per run. A run that is green but loads no new rows shows up here.

Backfill missed days (the DAG must be unpaused):

```bash
airflow backfill create --dag-id reference_pipeline --from-date 2026-09-07 --to-date 2026-09-09
```

🟡 [OPTIONAL]: one run per 06:00 in the range (here: two runs, labelled `backfill__...` in Grid).

```bash
ls .airflow/logs/dag_id=reference_pipeline/
```

🟡 [OPTIONAL]: one folder per run, one file per task attempt. This is what
debugging looks like six weeks from now.

**Slow tasks.** Airflow 3 no longer has SLAs. Each task has an
`execution_timeout` (20 minutes in our DAGs): a task that runs longer is
stopped and retried, and `logs/alerts.log` records it.
⚙️ [ADVANCED: can skip] Airflow 3's "deadline alerts" can warn when a whole
run is late; email alerts need an SMTP server. Discuss the idea, skip the setup.

Then the four incident logs in `day3/incidents/`: for each, the root cause;
retry, fix or escalate; and which signal caught it.

Discussion to close the day:

- Who gets paged when `ingest_api` fails at 06:00?
- What does "the pipeline is broken" mean: one failed task, or the whole DAG?
- When would you backfill, and when would you accept the gap?

### End-of-day cleanup

In the Airflow UI, pause both DAGs. Then:

```bash
make fail scenario=off
make airflow-stop
make api-stop
```

✅ [MUST RUN]: everything back to normal and stopped. Then stop the Codespace.

---

## One line to hand out at 5 pm

Airflow doesn't replace your loaders or your dbt code. It schedules them,
watches them, retries them, and tells you when they fail. The pipeline you
built on Days 1 and 2 is what runs; today was about the scaffolding that keeps
it running.
