"""hello: the smallest useful Airflow DAG (Day 3, Blocks 2 and 3).

Copy it into the DAGs folder to try it:

    cp templates/airflow_hello.py dags/hello.py

Within about 30 seconds it appears in the Airflow UI as "hello".

Three tasks, one after the other:

    start  ->  say_hello  ->  show_date

  start      EmptyOperator   does nothing; useful as a clear starting point
  say_hello  PythonOperator  calls the Python function greet()
  show_date  BashOperator    runs a shell command (this is how the lab
                             scripts and "dbt build" are run in a real DAG)
"""

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.python import PythonOperator
from airflow.sdk import DAG


def greet():
    """Anything printed here shows up in the task's Logs in the UI."""
    print("Hello from Airflow! This line was printed by a Python function.")


with DAG(
    dag_id="hello",
    schedule=None,                       # only runs when you trigger it
    start_date=pendulum.datetime(2026, 1, 1, tz="Asia/Singapore"),
    catchup=False,
    tags=["day3-demo"],
) as dag:
    start = EmptyOperator(task_id="start")
    say_hello = PythonOperator(task_id="say_hello", python_callable=greet)
    show_date = BashOperator(task_id="show_date", bash_command="date && echo 'Bash says hi'")

    # The arrows ARE the pipeline: run start, then say_hello, then show_date.
    start >> say_hello >> show_date
