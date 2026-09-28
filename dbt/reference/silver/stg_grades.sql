{{ config(schema='ref_silver', materialized='view') }}

-- stg_grades
-- Grain: one row per grade record (latest version by updated_at).
--
-- No row-level filtering. The orphan grade for S0999 is kept and flagged by
-- a warning-severity relationships test. Any score outside 0-100 is caught
-- by the singular test tests/assert_score_between_0_and_100.sql; it must
-- reach the test, not be silently filtered here.

with ranked as (
    select
        *,
        row_number() over (
            partition by record_id
            order by updated_at desc
        ) as rn
    from {{ source('bronze', 'api_grades') }}
)

select
    record_id,
    student_id,
    module_code,
    assessment,
    cast(score as integer) as score,
    updated_at
from ranked
where rn = 1
