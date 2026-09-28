{{ config(schema='ref_gold', materialized='table') }}

-- dim_student
-- Grain: one row per student (current values only, Type 1).
--
-- If we needed to track historical values (e.g. a student changing course),
-- we would use a dbt snapshot on ops.students and build a Type 2 dimension
-- from it. That is a Day 3 topic; here we keep Type 1 for simplicity.
--
-- The left join to the courses seed means DE99 (an orphan course code
-- known to the data contract) still appears in dim_student with a NULL
-- course_name, rather than being dropped.

select
    s.student_id,
    s.nric_hash,
    s.full_name,
    s.course_code,
    c.course_name,        -- NULL for DE99 (see stg_students schema)
    s.enrolment_date
from {{ ref('stg_students') }} s
left join {{ ref('courses') }} c
    using (course_code)
