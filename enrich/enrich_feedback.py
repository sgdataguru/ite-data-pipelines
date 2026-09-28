"""Day 2 Lab 3: enrich feedback comments with AI-classified sentiment.

Run from the repository root:

    python enrich/enrich_feedback.py

What the script does, in order:

  1. Reads data/feedback/feedback.csv.
  2. For every row, redacts personal data BEFORE any classifier sees it.
     Names, NRIC-shaped values, phone numbers and email addresses become
     [NAME], [NRIC], [PHONE], [EMAIL]. This is the "never send PII to a
     model" rule made concrete.
  3. Calls the AI stub to label the redacted comment as positive, neutral
     or negative. If the call fails, a tiny keyword rule takes over. The
     row is flagged needs_review = true so a human can double-check the
     fallback.
  4. Writes silver.feedback_enriched. The RAW comment is not stored -
     only the redacted version - because we don't need it downstream
     (data minimisation).
  5. Writes enrich/review_sample.md: 20 rows chosen with a fixed seed
     for the fairness discussion, including at least four Singlish
     comments.
  6. Prints a small summary at the end.

Environment:
    DUCKDB_PATH   points at the warehouse (defaults to warehouse/pipeline.duckdb)
    AI_STUB_FAIL  set to "1" to force every stub call to fail (for the demo)
"""

import csv
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path

import duckdb

# Local sibling module. The sys.path insert lets you run this from any
# directory: `python enrich/enrich_feedback.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ai_client import ai_client  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FEEDBACK_CSV = ROOT / "data" / "feedback" / "feedback.csv"
REVIEW_MD = ROOT / "enrich" / "review_sample.md"
SINGLISH_MARKERS = (
    "shiok", "sian", "atas", "sibei", "jialat", "chao ta", "buay tahan",
    "aiyoh", "wah lao", "aiya", "song ah", "steady bom", "song", "lor ",
    " lah", " lah.", " lah,", " liao", " sia", " ah ", " ah,", " ah.",
)

# --- Redaction --------------------------------------------------------------

NRIC_RE = re.compile(r"[STFGM][0-9]{7}[A-Z]")
# +65 phone numbers in the workshop pattern (+65 8000 0xxx). Kept
# permissive: any run of digits after the country code counts.
PHONE_RE = re.compile(r"\+65\s?\d{4}\s?\d{4}")
EMAIL_RE = re.compile(r"[A-Za-z0-9._+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def load_names(con):
    """Return every student name (full + given) we know about, for redaction.

    Reads from silver.stg_students first (that's the cleaned view). If
    Silver is not built yet, falls back to Bronze - the raw source.
    """
    def rows(table):
        return con.execute(f"SELECT full_name FROM {table}").fetchall()

    try:
        names = [r[0] for r in rows("ref_silver.stg_students")]
    except duckdb.Error:
        try:
            names = [r[0] for r in rows("silver.stg_students")]
        except duckdb.Error:
            names = [r[0] for r in rows("bronze.db_students")]

    entries = set()
    for name in names:
        if not name:
            continue
        entries.add(name)
        first = name.split()[0]
        if len(first) >= 3:  # avoid stripping ordinary short words like "Wei"
            entries.add(first)
    # Sort longest-first so "Wei Ling Tan" is matched before "Wei".
    return sorted(entries, key=len, reverse=True)


def redact_pii(text, names):
    """Return `text` with personal data replaced by category placeholders.

    Order matters: replace names first, then structured patterns.
    Substring matching is used for names (case-insensitive) because
    students write informally.
    """
    for n in names:
        text = re.compile(re.escape(n), re.IGNORECASE).sub("[NAME]", text)
    text = NRIC_RE.sub("[NRIC]", text)
    text = PHONE_RE.sub("[PHONE]", text)
    text = EMAIL_RE.sub("[EMAIL]", text)
    return text


# --- Fallback classifier ----------------------------------------------------

FALLBACK_POS = {"good", "great", "excellent", "best", "love", "loved", "clear"}
FALLBACK_NEG = {"hard", "confused", "boring", "waste", "terrible", "stressed"}


def rule_based_label(text):
    """Very small keyword fallback used when the AI stub is unavailable."""
    tokens = set(re.findall(r"[A-Za-z']+", text.lower()))
    if tokens & FALLBACK_POS and not tokens & FALLBACK_NEG:
        return "positive"
    if tokens & FALLBACK_NEG and not tokens & FALLBACK_POS:
        return "negative"
    return "neutral"


def enrich_feedback(text):
    """Provider-neutral. Swap ai_client for whatever ITE approves."""
    # 1. Never send personal data to a model.
    safe_text = redact_pii(text, enrich_feedback.names)
    try:
        label = ai_client.classify(
            safe_text, labels=["positive", "neutral", "negative"])
        # 2. Record which model produced the value.
        source = ai_client.model_id
    except Exception:
        # 3. Safe fallback keeps the pipeline running.
        label = rule_based_label(safe_text)
        source = "rules-v1"
    return {
        "label": label,
        "label_source": source,
        "needs_review": source == "rules-v1",
        "comment_redacted": safe_text,
    }


# The list of student names to redact is loaded once and cached on the
# function itself (avoids passing it through every call site).
enrich_feedback.names = []


# --- Persistence ------------------------------------------------------------

def write_enriched(con, enriched_rows):
    """Write silver.feedback_enriched. The raw comment is NOT stored."""
    con.execute("CREATE SCHEMA IF NOT EXISTS silver")
    con.execute("""
        CREATE OR REPLACE TABLE silver.feedback_enriched (
            feedback_id      VARCHAR,
            student_id       VARCHAR,
            module_code      VARCHAR,
            comment_redacted VARCHAR,
            label            VARCHAR,
            label_source     VARCHAR,
            needs_review     BOOLEAN,
            classified_at    TIMESTAMP
        )
    """)
    con.executemany("""
        INSERT INTO silver.feedback_enriched VALUES
        (?, ?, ?, ?, ?, ?, ?, ?)
    """, enriched_rows)


def looks_singlish(text):
    """Cheap heuristic: does the comment contain Singlish markers?"""
    low = " " + text.lower() + " "
    return any(marker in low for marker in SINGLISH_MARKERS)


def write_review_sample(rows_with_labels):
    """20 rows for the human review discussion; at least 4 Singlish."""
    rng = random.Random(20260918)  # fixed seed for reproducibility

    singlish = [r for r in rows_with_labels if looks_singlish(r["comment"])]
    standard = [r for r in rows_with_labels if not looks_singlish(r["comment"])]

    # Take enough Singlish to make the fairness discussion possible.
    min_singlish = min(4, len(singlish))
    sample = rng.sample(singlish, k=min_singlish)
    remainder = 20 - len(sample)
    sample.extend(rng.sample(standard, k=remainder))
    rng.shuffle(sample)

    with open(REVIEW_MD, "w") as f:
        f.write("# Feedback review sample\n\n")
        f.write("Twenty randomly selected rows for the Block 3 human review.\n")
        f.write("Mark Y or N under Agree? for each row, then swap notes with a partner.\n\n")
        f.write("| feedback_id | comment_redacted | label | Agree? (Y/N) |\n")
        f.write("|---|---|---|---|\n")
        for r in sample:
            comment = r["comment_redacted"].replace("|", "\\|")
            f.write(f"| {r['feedback_id']} | {comment} | {r['label']} |  |\n")


def main():
    warehouse = Path(os.environ.get(
        "DUCKDB_PATH",
        str(ROOT / "warehouse" / "pipeline.duckdb"),
    ))
    con = duckdb.connect(str(warehouse))

    enrich_feedback.names = load_names(con)

    # Read feedback.csv from disk (never touch Bronze - the raw comments
    # already sit in a CSV and we treat that as the source of truth).
    with open(FEEDBACK_CSV, newline="") as f:
        raw_rows = list(csv.DictReader(f))

    enriched, wide_rows = [], []
    for row in raw_rows:
        result = enrich_feedback(row["comment"])
        classified_at = datetime.now().replace(microsecond=0)
        enriched.append((
            row["feedback_id"], row["student_id"], row["module_code"],
            result["comment_redacted"], result["label"],
            result["label_source"], result["needs_review"], classified_at,
        ))
        wide_rows.append({**row, **result})

    write_enriched(con, enriched)
    write_review_sample(wide_rows)
    con.close()

    # Summary
    from collections import Counter
    by_source = Counter(r["label_source"] for r in wide_rows)
    needs_review = sum(1 for r in wide_rows if r["needs_review"])
    print(f"Processed {len(wide_rows)} rows")
    for source, count in sorted(by_source.items()):
        print(f"  label_source = {source!r}: {count}")
    print(f"  needs_review: {needs_review}")
    print(f"Wrote silver.feedback_enriched and {REVIEW_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
