{{ config(schema='ref_gold', materialized='table') }}

-- fct_attendance
-- Grain: one row per student, per module, per class date.
--
-- Every measure in this table can be aggregated cleanly along dim_student,
-- dim_module and dim_date, which is what makes a star schema easy to
-- report from. LATE counts as present for the "is_present" measure
-- because the student was in the classroom.

select
    concat_ws('|', a.student_id, a.module_code, cast(a.class_date as varchar))
        as attendance_key,
    a.student_id,
    a.module_code,
    a.class_date,
    a.attendance_status,
    case when a.attendance_status in ('PRESENT', 'LATE') then 1 else 0 end
        as is_present
from {{ ref('stg_attendance') }} a
