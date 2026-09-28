# Silver models

Cleaned, business-safe views over the Bronze tables. One file per staging model.

Naming convention: `stg_<source_thing>.sql`, e.g. `stg_attendance.sql`,
`stg_students.sql`, `stg_grades.sql`.

Materialisation: view (set at the folder level in `dbt_project.yml`).
