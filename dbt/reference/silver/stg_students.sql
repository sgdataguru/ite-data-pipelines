{{ config(schema='ref_silver', materialized='view') }}

-- stg_students
-- Grain: one row per student (latest version by updated_at).
--
-- Data minimisation: the only personal-data column that stays readable is
-- full_name. NRIC is hashed. Mobile, email and preferred_name are dropped
-- because no downstream model or report needs them.

with ranked as (
    select
        *,
        row_number() over (
            partition by student_id
            order by updated_at desc
        ) as rn
    from {{ source('bronze', 'db_students') }}
)

select
    student_id,
    {{ mask_pii('nric') }} as nric_hash,        -- hashed: raw NRIC never leaves Bronze
    full_name,                                  -- kept: needed for the roster display
    -- mobile: dropped (no downstream use case)
    -- email: dropped (no downstream use case)
    -- preferred_name: dropped (Scenario C artefact, not a business field)
    course_code,
    enrolment_date,
    updated_at
from ranked
where rn = 1
