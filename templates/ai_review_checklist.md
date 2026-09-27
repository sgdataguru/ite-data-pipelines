# AI Code Review Checklist

Code reviewed:

Reviewer:

| # | Check | Pass (Y/N) | Notes |
|---|---|---|---|
| 1 | Does it run? Does every imported library and function actually exist? | | |
| 2 | Does it do what was asked, including edge cases (empty data, last page, nulls)? | | |
| 3 | Are there timeouts, retries and clear error messages? | | |
| 4 | Are secrets read from the environment, never written in the code? | | |
| 5 | Is it idempotent? What happens if it runs twice? | | |
| 6 | Is any personal or confidential data sent anywhere it should not be, including to the AI tool itself? | | |
| 7 | Is the syntax current for the tool version we use? | | |
| 8 | Is there a test that proves it works? | | |
| 9 | Could you explain every line to a student? | | |
