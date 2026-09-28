{{ config(schema='ref_gold', materialized='table') }}

-- dim_date
-- Grain: one row per calendar day, from the earliest to the latest class
-- date currently in stg_attendance.
--
-- Built with DuckDB's generate_series. Regenerated on every build; if the
-- date range in Silver grows, the dimension grows to match.

with bounds as (
    select
        min(class_date) as first_day,
        max(class_date) as last_day
    from {{ ref('stg_attendance') }}
)

select
    date_day,
    strftime(date_day, '%A')  as day_name,
    date_part('week', date_day) as iso_week,
    date_trunc('week', date_day)::date as week_start,
    dayofweek(date_day) in (0, 6) as is_weekend
from bounds,
     unnest(generate_series(first_day, last_day, interval 1 day)) as g(date_day)
