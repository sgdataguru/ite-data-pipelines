{{ config(schema='ref_silver', materialized='view') }}

-- stg_attendance
-- Grain: one row per student, per class date, per module.
--
-- Cleans bronze.file_attendance for downstream use. Every filter below is
-- deliberate: each one handles a Day 2 defect that was planted in Bronze
-- during data generation (see the facilitator notes).

with ranked as (
    select
        *,
        -- The newest row (by _ingested_at) for each (student, day, module)
        -- combination gets rn = 1; earlier duplicates are dropped.
        row_number() over (
            partition by student_id, class_date, module_code
            order by _ingested_at desc
        ) as rn
    from {{ source('bronze', 'file_attendance') }}
)

select
    student_id,
    class_date,
    module_code,
    upper(trim(status)) as attendance_status
from ranked
where rn = 1                                                       -- duplicates
  and upper(trim(status)) in ('PRESENT', 'ABSENT', 'LATE', 'MC')   -- invalid status ("PRESNT")
  and module_code is not null                                      -- missing module
  and class_date <= current_date                                   -- future date
  and student_id in (                                              -- orphan student
      select student_id from {{ source('bronze', 'db_students') }}
  )
