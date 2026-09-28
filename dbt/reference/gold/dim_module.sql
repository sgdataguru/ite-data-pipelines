{{ config(schema='ref_gold', materialized='table') }}

-- dim_module
-- Grain: one row per module.
--
-- Built directly from the modules seed. The seed is small (12 rows) and
-- rarely changes, so it is the single source of truth for module names.

select
    module_code,
    module_name
from {{ ref('modules') }}
