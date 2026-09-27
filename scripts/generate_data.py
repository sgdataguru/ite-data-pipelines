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


def main():
    rng = random.Random(SEED)
    students = build_students(rng)
    write_student_db(students)
    write_attendance(rng, students)
    write_grades(rng, students)
    print("Synthetic data written to sources/, data/ and mock_api/grades_seed.json")


if __name__ == "__main__":
    main()
