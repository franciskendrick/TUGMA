# Profile, class-schedule, and availability management.
# Every function re-checks the caller's role against the database.

import re
import sqlite3

from services.auth_service import AuthError, require_role

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
LANGUAGES = ["Filipino", "English"]
TIME_PATTERN = re.compile(r"^([01][0-9]|2[0-3]):[0-5][0-9]$")


def _check_interval(day, start, end):
    if day not in DAYS:
        raise AuthError("Choose a day from Monday to Saturday.")
    if not (TIME_PATTERN.match(start) and TIME_PATTERN.match(end)):
        raise AuthError("Enter times as HH:MM.")
    if start >= end:
        raise AuthError("The start time must be before the end time.")


def _overlaps(db, table, owner_col, owner_id, day, start, end, exclude=None):
    row = db.fetch_one(
        f"SELECT 1 FROM {table} WHERE {owner_col} = ? AND day = ? "
        "AND start_time < ? AND end_time > ?",
        (owner_id, day, end, start),
    )
    return row is not None


# ------------------------------------------------------------ profiles
def add_profile(db, user_id, kind):
    """Give a member the other profile (student <-> tutor)."""
    user = require_role(db, user_id, "member")
    column = "student_id" if kind == "student" else "tutor_id"
    if kind not in ("student", "tutor") or user[column] is not None:
        raise AuthError("You already have this profile.")

    source = db.fetch_one(
        "SELECT name, grade_level, course FROM "
        + ("tutors WHERE tutor_id" if kind == "student" else "students WHERE student_id")
        + " = ?",
        (user["tutor_id"] if kind == "student" else user["student_id"],),
    )
    connection = db.connect()
    try:
        if kind == "student":
            cursor = connection.execute(
                "INSERT INTO students (name, grade_level, course) VALUES (?, ?, ?)",
                tuple(source),
            )
        else:
            cursor = connection.execute(
                "INSERT INTO tutors (name, grade_level, course, verified) "
                "VALUES (?, ?, ?, 0)",
                tuple(source),
            )
        connection.execute(
            f"UPDATE users SET {column} = ? WHERE user_id = ?",
            (cursor.lastrowid, user_id),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def set_languages(db, user_id, kind, languages):
    user = require_role(db, user_id, kind)
    owner = user[f"{kind}_id"]
    table = f"{kind}_languages"
    if not languages or any(l not in LANGUAGES for l in languages):
        raise AuthError("Choose at least one language.")
    connection = db.connect()
    try:
        connection.execute(f"DELETE FROM {table} WHERE {kind}_id = ?", (owner,))
        connection.executemany(
            f"INSERT INTO {table} ({kind}_id, language) VALUES (?, ?)",
            [(owner, l) for l in languages],
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def set_capacity(db, user_id, capacity):
    user = require_role(db, user_id, "tutor")
    if not isinstance(capacity, int) or not 1 <= capacity <= 50:
        raise AuthError("Capacity must be between 1 and 50.")
    db.execute("UPDATE tutors SET capacity = ? WHERE tutor_id = ?",
               (capacity, user["tutor_id"]))


def set_tutor_verified(db, admin_user_id, tutor_id, verified):
    require_role(db, admin_user_id, "admin")
    cursor = db.execute("UPDATE tutors SET verified = ? WHERE tutor_id = ?",
                        (1 if verified else 0, tutor_id))
    if cursor.rowcount == 0:
        raise AuthError("That tutor does not exist.")


# ----------------------------------------------------- subjects (needs)
def add_need(db, user_id, subject_id, note=""):
    user = require_role(db, user_id, "student")
    try:
        db.execute(
            "INSERT INTO student_subjects (student_id, subject_id, note) "
            "VALUES (?, ?, ?)",
            (user["student_id"], subject_id, (note or "").strip()[:200] or None),
        )
    except sqlite3.IntegrityError as error:
        raise AuthError("That class is already on your list.") from error


def remove_need(db, user_id, subject_id):
    user = require_role(db, user_id, "student")
    db.execute("DELETE FROM student_subjects WHERE student_id = ? AND subject_id = ?",
               (user["student_id"], subject_id))


def add_teach(db, user_id, subject_id):
    user = require_role(db, user_id, "tutor")
    try:
        db.execute("INSERT INTO tutor_subjects (tutor_id, subject_id) VALUES (?, ?)",
                   (user["tutor_id"], subject_id))
    except sqlite3.IntegrityError as error:
        raise AuthError("You already teach that subject.") from error


def remove_teach(db, user_id, subject_id):
    user = require_role(db, user_id, "tutor")
    db.execute("DELETE FROM tutor_subjects WHERE tutor_id = ? AND subject_id = ?",
               (user["tutor_id"], subject_id))


# ---------------------------------------------------- classes (student)
def add_class(db, user_id, subject_id, day, start, end):
    user = require_role(db, user_id, "student")
    _check_interval(day, start, end)
    if _overlaps(db, "student_schedule", "student_id", user["student_id"],
                 day, start, end):
        raise AuthError("This class overlaps another class on your schedule.")
    try:
        db.execute(
            "INSERT INTO student_schedule "
            "(student_id, day, start_time, end_time, subject_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (user["student_id"], day, start, end, subject_id),
        )
    except sqlite3.IntegrityError as error:
        raise AuthError("Choose a subject from the list.") from error


def delete_class(db, user_id, schedule_id):
    user = require_role(db, user_id, "student")
    db.execute("DELETE FROM student_schedule WHERE schedule_id = ? AND student_id = ?",
               (schedule_id, user["student_id"]))


# ---------------------------------------------- availability (tutor)
def add_availability(db, user_id, day, start, end, subject_id=None):
    user = require_role(db, user_id, "tutor")
    _check_interval(day, start, end)
    if _overlaps(db, "tutor_availability", "tutor_id", user["tutor_id"],
                 day, start, end):
        raise AuthError("This overlaps availability you already added.")
    # A person who is also a student cannot tutor during their own classes.
    if user["student_id"] is not None and _overlaps(
        db, "student_schedule", "student_id", user["student_id"], day, start, end
    ):
        raise AuthError("This overlaps one of your own classes.")
    db.execute(
        "INSERT INTO tutor_availability (tutor_id, subject_id, day, start_time, end_time) "
        "VALUES (?, ?, ?, ?, ?)",
        (user["tutor_id"], subject_id, day, start, end),
    )


def delete_availability(db, user_id, availability_id):
    user = require_role(db, user_id, "tutor")
    db.execute(
        "DELETE FROM tutor_availability WHERE availability_id = ? AND tutor_id = ?",
        (availability_id, user["tutor_id"]),
    )
