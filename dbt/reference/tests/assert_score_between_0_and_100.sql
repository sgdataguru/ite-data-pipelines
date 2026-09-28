-- Singular test: no grade should have a score below 0 or above 100.
--
-- Returns the offending rows. An empty result means the test passes.
-- Severity defaults to error, so this is the one that catches the
-- "make fail scenario=dq" injection (a grade with score = 150).

select record_id, student_id, module_code, score
from {{ ref('stg_grades') }}
where score < 0 or score > 100
