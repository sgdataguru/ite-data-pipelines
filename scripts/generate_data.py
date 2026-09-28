"""Generate all synthetic workshop data.

Run from the repository root:

    python scripts/generate_data.py

Everything is generated from a fixed random seed, so running this again
produces exactly the same files. ALL DATA IS SYNTHETIC: the names are
invented, the NRICs have a deliberately wrong check letter, the emails use
example.com and the mobile numbers use the unused +65 8000 0xxx range.

Outputs:
    sources/ops.db, sources/ops_original.db   student database (SQLite)
    data/attendance/attendance_2026-09-07.csv ... _2026-09-11.csv
    data/fixtures/attendance_corrupt.csv      used by "make fail scenario=b"
    mock_api/grades_seed.json                 served by the mock grades API

Defects planted on purpose (they are used in the Day 1 and Day 2 labs) are
listed in plant_attendance_defects() and in the facilitator notes.
"""

import csv
import json
import random
import shutil
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

SEED = 2026
ROOT = Path(__file__).resolve().parent.parent

# All "updated_at" values are spread over the 30 days before this moment.
# It is fixed (not "now") so the data is identical every time.
ANCHOR = datetime(2026, 9, 25, 18, 0, 0)

COURSES = [
    ("DE01", "Higher Nitec in Data Engineering"),
    ("CS01", "Higher Nitec in Cyber Security"),
    ("IT01", "Higher Nitec in IT Applications Development"),
    ("BA01", "Higher Nitec in Business Analytics"),
]

# Two or more modules per course. Each school day a student attends two.
MODULES = {
    "DE01": ["DE101", "DE102", "DE103"],
    "CS01": ["CS101", "CS102", "CS103"],
    "IT01": ["IT101", "IT102", "IT103"],
    "BA01": ["BA101", "BA102", "BA103"],
}

# Invented names reflecting Singapore's mix. (first name, last name).
# The email address is built from these two parts.
NAMES = [
    ("Wei Ling", "Tan"), ("Jun Hao", "Lim"), ("Nurul Aisyah", "Rahman"),
    ("Arjun", "Pillai"), ("Mei Xin", "Goh"), ("Muhammad Irfan", "Hassan"),
    ("Priya", "Nair"), ("Kai Wen", "Ong"), ("Siti Nurhaliza", "Osman"),
    ("Daniel", "De Souza"), ("Hui Min", "Chua"), ("Farhan", "Ismail"),
    ("Kavitha", "Raman"), ("Zhi Hao", "Teo"), ("Aisyah", "Salleh"),
    ("Ryan", "Pereira"), ("Xin Yi", "Koh"), ("Haziq", "Aziz"),
    ("Deepa", "Krishnan"), ("Jia Hui", "Ng"), ("Amirul", "Hakim"),
    ("Rachel", "Fernandez"), ("Yu Xuan", "Seah"), ("Nabilah", "Yusof"),
    ("Vikram", "Menon"), ("Shu Ting", "Wong"), ("Hafiz", "Rosli"),
    ("Clara", "Rodrigues"), ("Jing Yi", "Lee"), ("Syafiq", "Latiff"),
    ("Anjali", "Subramaniam"), ("Wen Jie", "Yeo"), ("Nur Iman", "Kamal"),
    ("Marcus", "Sequeira"), ("Si Min", "Low"), ("Adib", "Rashid"),
    ("Lakshmi", "Iyer"), ("Jun Jie", "Chan"), ("Hidayah", "Jamil"),
    ("Joshua", "D'Cruz"),
]

ASSESSMENTS = ["Quiz 1", "Quiz 2", "Lab Test", "Project", "Final Exam"]
SCHOOL_DAYS = [date(2026, 9, 7) + timedelta(days=i) for i in range(5)]
CORRUPT_DAY = date(2026, 9, 14)


# ---------------------------------------------------------------------------
# Student database
# ---------------------------------------------------------------------------

def fake_nric(rng):
    """Return an NRIC-shaped string whose check letter is deliberately WRONG.

    The real checksum is calculated, then a different letter is used, so the
    value can never match a real NRIC.
    """
    prefix = rng.choice("ST")
    digits = [rng.randint(0, 9) for _ in range(7)]
    weights = [2, 7, 6, 5, 4, 3, 2]
    total = sum(d * w for d, w in zip(digits, weights))
    if prefix == "T":
        total += 4
    letters = "JZIHGFEDCBA"
    correct = letters[total % 11]
    wrong = letters[(letters.index(correct) + 1) % 11]  # always different
    return prefix + "".join(str(d) for d in digits) + wrong


def random_time_in_last_30_days(rng):
    """A timestamp somewhere in the 30 days before ANCHOR, to the second."""
    seconds = rng.randint(0, 30 * 24 * 3600 - 1)
    return ANCHOR - timedelta(seconds=seconds)


def build_students(rng):
    students = []
    course_codes = [c[0] for c in COURSES]
    for i, (first, last) in enumerate(NAMES, start=1):
        student_id = f"S{i:04d}"
        course = course_codes[(i - 1) % len(course_codes)]
        if student_id == "S0040":
            course = "DE99"  # DAY 2 DEFECT: orphan key, not in courses
        email_first = first.lower().replace(" ", "")
        email_last = last.lower().replace(" ", "").replace("'", "")
        students.append({
            "student_id": student_id,
            "nric": fake_nric(rng),
            "full_name": f"{first} {last}",
            "email": f"{email_first}.{email_last}@example.com",
            "mobile": f"+65 8000 0{i:03d}",
            "course_code": course,
            "enrolment_date": rng.choice(["2025-04-14", "2026-04-13"]),
            "updated_at": random_time_in_last_30_days(rng).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return students


def write_student_db(students):
    db_path = ROOT / "sources" / "ops.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE courses (
            course_code TEXT PRIMARY KEY,
            course_name TEXT
        )""")
    # updated_at is declared TIMESTAMP so DuckDB's SQLite reader returns
    # a real timestamp rather than text.
    con.execute("""
        CREATE TABLE students (
            student_id     TEXT PRIMARY KEY,
            nric           TEXT,
            full_name      TEXT,
            email          TEXT,
            mobile         TEXT,
            course_code    TEXT,
            enrolment_date DATE,
            updated_at     TIMESTAMP
        )""")
    con.executemany("INSERT INTO courses VALUES (?, ?)", COURSES)
    con.executemany(
        "INSERT INTO students VALUES (:student_id, :nric, :full_name, :email,"
        " :mobile, :course_code, :enrolment_date, :updated_at)",
        students,
    )
    con.commit()
    con.close()

    # Clean copy, used by "make fail scenario=off" to undo Scenario C.
    shutil.copyfile(db_path, ROOT / "sources" / "ops_original.db")


# ---------------------------------------------------------------------------
# Attendance files
# ---------------------------------------------------------------------------

def modules_for(student, day_index):
    """The two modules a student attends on a given school day."""
    course = student["course_code"]
    mods = MODULES.get(course, MODULES["DE01"])  # orphan DE99 student
    first = mods[day_index % len(mods)]
    second = mods[(day_index + 1) % len(mods)]
    return [first, second]


def random_status(rng):
    return rng.choices(["PRESENT", "ABSENT", "LATE", "MC"], weights=[82, 7, 7, 4])[0]


def build_day(rng, students, day, day_index):
    """Rows for one day: every student, two modules. Rows are lists of text."""
    rows = []
    for s in students:
        for module in modules_for(s, day_index):
            rows.append([s["student_id"], day.isoformat(), module, random_status(rng)])
    return rows


def plant_attendance_defects(files):
    """Plant the Day 1 and Day 2 defects. `files` maps a date to its rows.

    Day 1 (must be REJECTED by read_csv, exactly two rows in total):
      - one row with an extra column              (2026-09-08)
      - one row with an unparseable date 2026-13-45 (2026-09-10)
    Day 2 (must LOAD into Bronze as valid rows):
      - 3 exact duplicate rows
      - 2 rows with status 'PRESNT'
      - 2 rows with an empty module_code
      - 1 row with class_date in 2027
      - 1 row with student_id 'S0999' (not in students)
    """
    d = {day: rows for day, rows in files.items()}
    mon, tue, wed, thu, fri = SCHOOL_DAYS

    # Day 2: exact duplicates (copy an existing row and add it again)
    d[mon].insert(11, list(d[mon][10]))
    d[wed].insert(31, list(d[wed][30]))
    d[fri].insert(51, list(d[fri][50]))

    # Day 2: misspelt status
    d[tue][5][3] = "PRESNT"
    d[thu][22][3] = "PRESNT"

    # Day 2: empty module_code
    d[mon][40][2] = ""
    d[fri][15][2] = ""

    # Day 2: a class date in the future
    d[thu][60][1] = "2027-09-10"

    # Day 2: a student who does not exist
    d[wed].append(["S0999", wed.isoformat(), "DE101", "PRESENT"])

    # Day 1: malformed rows (placed well after the header)
    d[tue].insert(45, ["S0012", tue.isoformat(), "IT102", "PRESENT", "extra"])
    d[thu].insert(35, ["S0021", "2026-13-45", "DE102", "PRESENT"])
    return d


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["student_id", "class_date", "module_code", "status"])
        writer.writerows(rows)


def write_attendance(rng, students):
    folder = ROOT / "data" / "attendance"
    for old in folder.glob("attendance_*.csv"):
        old.unlink()

    files = {day: build_day(rng, students, day, i) for i, day in enumerate(SCHOOL_DAYS)}
    files = plant_attendance_defects(files)
    for day, rows in files.items():
        write_csv(folder / f"attendance_{day.isoformat()}.csv", rows)

    # Fixture for Scenario B: a sixth day with exactly 5 malformed rows.
    rows = build_day(rng, students, CORRUPT_DAY, 5)
    rows[8].append("extra")                         # too many columns
    rows[27].append("left early")                   # too many columns
    rows[44] = rows[44][:3]                         # too few columns
    rows[61][1] = "2026-09-31"                      # invalid date
    rows[73][1] = "14/09/2026"                      # wrong date format
    write_csv(ROOT / "data" / "fixtures" / "attendance_corrupt.csv", rows)


# ---------------------------------------------------------------------------
# Grades (served by the mock API)
# ---------------------------------------------------------------------------

def write_grades(rng, students):
    records = []
    for record_id in range(1, 201):
        s = rng.choice(students)
        student_id = s["student_id"]
        if record_id == 137:
            student_id = "S0999"  # DAY 2 DEFECT: orphan key
        records.append({
            "record_id": record_id,
            "student_id": student_id,
            "module_code": rng.choice(modules_for(s, rng.randint(0, 2))),
            "assessment": rng.choice(ASSESSMENTS),
            "score": rng.randint(35, 100),
            "updated_at": random_time_in_last_30_days(rng).isoformat(),
        })
    path = ROOT / "mock_api" / "grades_seed.json"
    path.write_text(json.dumps(records, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Feedback comments (Day 2 - AI enrichment lab)
# ---------------------------------------------------------------------------

# Template libraries. Each template mentions {module_name} so the same
# sentence works for any module. Standard-English templates read like a
# polytechnic student typing quickly; Singlish templates use natural
# Singapore English particles.

POSITIVE_STD = [
    "Really enjoyed the {module_name} class today, exercises were clear",
    "The {module_name} lab was great, learned a lot from the examples",
    "Prof explained {module_name} very well, made the topic click",
    "Best {module_name} session so far, the pace was just right",
    "Loved the {module_name} project brief, super interesting problem",
    "{module_name} is finally making sense after today's tutorial",
    "The quiz for {module_name} was fair and covered the right stuff",
    "{module_name} homework was tough but rewarding, will remember this",
    "Group work in {module_name} today was actually fun for once",
    "The {module_name} lecturer is patient with our questions, thanks",
    "{module_name} demo was excellent, seeing the code run helped a lot",
    "Feeling motivated after the {module_name} class, want to do more",
    "The extra reading for {module_name} was really useful",
    "Class today for {module_name} was engaging start to finish",
    "{module_name} exam prep session was very helpfull",
    "Really appreciated the walkthrough on {module_name} today",
    "The {module_name} case study was interesting and relevant",
    "Enjoyed the {module_name} discussion, everyone contributed",
    "{module_name} project feedback was constructive, thanks prof",
    "Feels good to finally understand {module_name}",
]

NEUTRAL_STD = [
    "The {module_name} class was ok today, nothing special",
    "{module_name} lecture was fine i guess, average",
    "Just another {module_name} tutorial, no complaints",
    "{module_name} lab today was so-so, some parts clear some not",
    "The pace of {module_name} was fine, could have been faster",
    "{module_name} content was fine but the slides could be better",
    "Attended {module_name} today, standard class",
    "Not sure how i feel about the {module_name} project yet",
    "The {module_name} recap was ok, hoping the next one is deeper",
    "{module_name} was fine today, felt neutral about it",
    "Half the {module_name} session was useful, half was known already",
    "Not much to say about the {module_name} class, was standard",
    "{module_name} today just passed by, nothing memorable",
    "{module_name} was neither good nor bad this week",
    "Fine class for {module_name}, nothing to write home about",
]

NEGATIVE_STD = [
    "The {module_name} project deadline is way too tight, super stressed",
    "Confused after the {module_name} lecture, examples went too fast",
    "{module_name} lab was frustrating, instructions unclear",
    "Boring {module_name} session, no examples at all",
    "Please make the {module_name} exercises less hard, its exhausting",
    "Getting lost in {module_name} content, feels like too much",
    "{module_name} quiz was unfair, covered stuff we did not do",
    "Terrible {module_name} class today, wasted the hour",
    "Overwhelmed by the {module_name} assignment volume",
    "The {module_name} tutorial dragged on with no clear point",
    "Struggling with {module_name} homework, no support",
    "{module_name} class was chaotic today, hard to follow",
    "Hate the way {module_name} is being taught this semester",
    "Not getting anything from the {module_name} lectures anymore",
    "{module_name} coursework is way too heavy, cannot cope",
    "Please stop the pop quizes in {module_name}, so stressful",
    "The {module_name} module needs a serious redesign",
    "{module_name} last class was a waste of everyones time",
    "Nothing about {module_name} today made sense",
    "I dread every {module_name} tutorial now honestly",
]

# Singlish comments. Deliberately colloquial - kept respectful. The stub
# classifier in enrich/ai_client.py will get many of these wrong on purpose,
# so participants see the fairness point without contrived numbers.
POSITIVE_SG = [
    "The {module_name} lab damn shiok lah, atas siol!",
    "Wah steady the {module_name} session today, sibei on",
    "{module_name} teacher damn on lah, super power",
    "Song ah the {module_name} tutorial, understand liao",
    "Very shiok the {module_name} practical, best one so far",
]

NEUTRAL_SG = [
    "{module_name} class today just so-so lah, no strong feeling",
    "Aiya {module_name} lecture ok only, nothing to shout about",
    "The {module_name} tutorial neither shiok nor sian, just there lor",
    "Class today for {module_name} passed like that lah, standard",
]

NEGATIVE_SG = [
    "Sian ah, the {module_name} assessment hard until want give up",
    "Teacher explain {module_name} until very blur, cannot catch",
    "{module_name} project chao ta already lah",
    "Wah lao {module_name} homework buay tahan sia",
    "{module_name} class jialat sibei, everyone also confuse",
    "Aiyoh the {module_name} pace too fast for me",
]

FEEDBACK_ROWS = 100      # total feedback rows
PII_ROWS = 10            # rows in which we inject a personal-data value
SINGLISH_ROWS = 15       # rows written in Singlish


# Module name lookup - kept aligned with seeds/modules.csv by hand.
MODULE_NAMES = {
    "DE101": "Data Fundamentals", "DE102": "Data Pipelining",
    "DE103": "Data Storage and Retrieval",
    "CS101": "Cyber Security Fundamentals", "CS102": "Network Security",
    "CS103": "Incident Response",
    "IT101": "Programming Fundamentals",
    "IT102": "Web Applications Development",
    "IT103": "Mobile Applications Development",
    "BA101": "Business Analytics Fundamentals",
    "BA102": "Data Visualisation", "BA103": "Predictive Analytics",
}


def module_lookup(rng, module_codes):
    """Pick a module code and its human name (from the seed list)."""
    code = rng.choice(module_codes)
    return code, MODULE_NAMES[code]


def build_feedback(rng, students):
    """Build (rows, labels) where rows is written to the repo and labels stays
    in the facilitator notes."""
    module_codes = sorted({m for mods in MODULES.values() for m in mods})

    # Compose a plan: which slots are Singlish, which sentiment for each.
    # Rough distribution: 45 positive, 25 neutral, 30 negative.
    plan = (
        [("standard", "positive")] * (45 - 3)
        + [("standard", "neutral")] * (25 - 2)
        + [("standard", "negative")] * (30 - 10)
        + [("singlish", "positive")] * 3
        + [("singlish", "neutral")] * 2
        + [("singlish", "negative")] * 10
    )
    assert len(plan) == FEEDBACK_ROWS
    rng.shuffle(plan)

    # Choose which slot indices carry personal data. Pick evenly across
    # the four PII kinds (name, NRIC, phone, email).
    pii_slots = rng.sample(range(FEEDBACK_ROWS), PII_ROWS)
    pii_kinds = ["name", "nric", "phone", "email"] * 3  # >= 10
    rng.shuffle(pii_kinds)
    pii_kinds = pii_kinds[:PII_ROWS]

    library = {
        ("standard", "positive"): POSITIVE_STD,
        ("standard", "neutral"): NEUTRAL_STD,
        ("standard", "negative"): NEGATIVE_STD,
        ("singlish", "positive"): POSITIVE_SG,
        ("singlish", "neutral"): NEUTRAL_SG,
        ("singlish", "negative"): NEGATIVE_SG,
    }

    rows, labels = [], []
    for idx, (group, sentiment) in enumerate(plan):
        student = rng.choice(students)
        module_code, module_name = module_lookup(rng, module_codes)
        template = rng.choice(library[(group, sentiment)])
        comment = template.format(module_name=module_name)

        # Injection: append a sentence that carries the personal detail.
        if idx in pii_slots:
            slot_position = pii_slots.index(idx)
            kind = pii_kinds[slot_position]
            if kind == "name":
                comment += f". Btw my name is {student['full_name']}"
            elif kind == "nric":
                comment += f". My matric is fine but for the record my nric is {student['nric']}"
            elif kind == "phone":
                comment += f". Call me back at {student['mobile']} if you want"
            elif kind == "email":
                comment += f". Reply to me at {student['email']}"

        submitted_at = random_time_in_last_30_days(rng).isoformat(sep=" ", timespec="seconds")
        feedback_id = f"F{idx + 1:04d}"

        rows.append({
            "feedback_id": feedback_id,
            "student_id": student["student_id"],
            "module_code": module_code,
            "submitted_at": submitted_at,
            "comment": comment,
        })
        labels.append({
            "feedback_id": feedback_id,
            "true_label": sentiment,
            "group": group,
        })
    return rows, labels


def write_feedback(rows, labels):
    """Feedback data goes in the repository; labels go in the facilitator notes."""
    csv_path = ROOT / "data" / "feedback" / "feedback.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # Facilitator-only. This folder sits BESIDE the repository, not inside
    # it, so a student who clones the repo never gets the answer key.
    labels_dir = ROOT.parent / "ite-facilitator-notes"
    labels_dir.mkdir(parents=True, exist_ok=True)
    labels_path = labels_dir / "feedback_labels.csv"
    with open(labels_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(labels[0].keys()))
        writer.writeheader()
        writer.writerows(labels)


def main():
    rng = random.Random(SEED)
    students = build_students(rng)
    write_student_db(students)
    write_attendance(rng, students)
    write_grades(rng, students)
    feedback_rows, feedback_labels = build_feedback(rng, students)
    write_feedback(feedback_rows, feedback_labels)
    print("Synthetic data written to sources/, data/, mock_api/grades_seed.json "
          "and data/feedback/feedback.csv (labels in ../ite-facilitator-notes/)")


if __name__ == "__main__":
    main()
