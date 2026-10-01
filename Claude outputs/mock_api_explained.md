# The mock grades API, explained

Facilitators only. How it works behind the scenes, and how to explain it in class.

## The short answer

The mock API is a small web service **we wrote ourselves**, running **inside
each participant's Codespace**. It does not connect to the internet or to any
real school system. It serves **200 made-up grade records** from a file in the
repository, and it can be told to misbehave on purpose. Every participant gets
the same 200 records.

## The four pieces

| Piece | File | What it does |
|---|---|---|
| The data | `mock_api/grades_seed.json` | 200 synthetic grade records. Each has `record_id`, `student_id`, `module_code`, `assessment`, `score` and `updated_at`. |
| Where the data came from | `scripts/generate_data.py` | Wrote the file once, using Python's random generator with a **fixed seed**. "Random" but identical every time it is run, so every Codespace has the same data and the expected answers (200 rows, 4 pages) are always right. The same script made the attendance CSVs and the student database. |
| The server | `mock_api/app.py` | A FastAPI app (about 150 lines). `make api` starts it with Uvicorn on port 8000, in the background, log in `logs/api.log`. |
| The switch | `mock_api/state.json`, written by `make fail scenario=...` | Tells the server how to misbehave. The server re-reads it on every request, so a new scenario works immediately, with no restart. |

## What happens on one request

The client is the participant's script, `lab2/.../ingest_api.py`. It sends:

```
GET http://localhost:8000/records?updated_since=1900-01-01T00:00:00&limit=500
Authorization: Bearer workshop-token-not-a-real-secret
```

The server then works through four steps, in order:

1. **Check the token.** If the header does not match `SOURCE_API_TOKEN`, answer **401** "Invalid or missing token".
2. **Check the switch.** Read `state.json`:
   - `auth` means answer **401** "Token expired".
   - `a` means answer **500** for 30 seconds, then recover.
   - `ratelimit` means answer **429** to two of every three requests.
   - `off` means behave normally.
3. **Filter.** Keep only records with `updated_at` later than `updated_since`. This is what makes the load incremental.
4. **Cut one page.** Take at most **50** records from the cursor position, and send them back with the bookmark for the next page:

```json
{ "data": [ {record 1}, ..., {record 50} ], "next_cursor": "NTA=" }
```

On the last page, `next_cursor` is `null`.

That is the whole server. The client script then inserts what it received
into DuckDB (`bronze.api_grades`), adding the three metadata columns.

## Pagination in plain words

**The analogy: a bank statement.** You ask the bank for all your
transactions. They do not hand you 2,000 lines on one sheet. They send page 1
of 4, and at the bottom it says "continued on page 2". You keep asking for the
next page until one says "last page".

- **Page size.** The client asks for 500 at a time, but this server never gives
  more than 50 per page. Real APIs do the same: they protect themselves by
  capping page size. So 200 records arrive as **4 pages of 50**.
- **The cursor is the bookmark.** `next_cursor` says "start here next time".
  The client sends it back unchanged with its next request. It looks like
  gibberish (`NTA=`); inside it is just "position 50", encoded. The client is
  not meant to understand it, only to hand it back. That is what "opaque
  cursor" means.
- **`null` means the last page.** When `next_cursor` is `null`, stop. A loop
  that forgets this check asks for ever: the defect in the Day 1 AI sample.

**Why APIs page at all:** one huge answer is slow, uses a lot of memory on
both sides, and one network blip means starting again. Pages keep each
answer small and let you pick up where you left off.

## The watermark in plain words

**The analogy: a newspaper delivery.** You don't want every paper ever
printed each morning, only the ones since yesterday. The watermark is
"the date of the newest paper I already have".

The script looks up the newest `updated_at` already in `bronze.api_grades`
and asks the API only for records updated after it:

- **First run:** Bronze is empty, so the watermark is `1900-01-01`. The script gets all 200 records in 4 pages.
- **Second run:** the watermark is `2026-09-25T12:09:52`, the newest record. The API returns 0 records on 1 page, and 0 rows are inserted.

Pagination and the watermark answer two different questions. Pagination is
"how do I receive a big answer in pieces?". The watermark is "how do I ask
only for what is new?".

## Where the data ends up

```
grades_seed.json ──> mock API (port 8000) ──HTTP pages──> ingest_api.py ──> bronze.api_grades (DuckDB)
```

The records in `bronze.api_grades` are exactly the ones in
`grades_seed.json`. Participants can check this:

```bash
python scripts/query.py "SELECT count(*) FROM bronze.api_grades"                           # 200
```

The raw answer, straight from the API (one line; paste as is):

```bash
curl -s -H "Authorization: Bearer $SOURCE_API_TOKEN" "localhost:8000/records?limit=500" | python -c "import json,sys; p=json.load(sys.stdin); print(len(p['data']), 'records, next_cursor =', p['next_cursor']); print(p['data'][0])"
```

It prints:

```
50 records, next_cursor = NTA=
{'record_id': 181, 'student_id': 'S0002', 'module_code': 'CS102', 'assessment': 'Final Exam', 'score': 53, 'updated_at': '2026-08-26T18:15:22'}
```

The `curl` line is a good live demo: asked for 500, got 50, plus the
bookmark for the next page, before any Python.

## Talk track for the 2:40 demo (about two minutes)

**SAY** "This API is running inside your own Codespace. We built it, so we can
break it on purpose. It holds 200 fake grades. Real vendor APIs work the same
way; this one just never goes down unless I tell it to."

**DO** Run the `curl` line. Point at `data` and `next_cursor`.

**SAY** "We asked for 500 and got 50. The API decides the page size, not us.
And at the bottom there's a bookmark: next_cursor. Think of a bank statement:
'continued on page 2'. Your code keeps asking for the next page until the
bookmark is empty. That's pagination."

**SAY** "Second idea: the watermark. We only ask for grades changed since the
newest one we already have. First run: everything, four pages. Second run:
nothing new, zero rows. Same idea as the database this morning."

## Why this design suits a classroom

- **No internet dependency.** Each Codespace has its own copy, so Wi-Fi or an outside service cannot stop the lab.
- **Same data everywhere.** Everyone expects 200 rows and 4 pages; a different number means a bug.
- **Failures on demand.** Real outages cannot be scheduled for 3:48 pm; this one can.
- **Nothing real at risk.** Synthetic data and a fake token build the right habits (token from the environment, no real student data) with no PDPA exposure.
