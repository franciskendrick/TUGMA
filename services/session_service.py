# Tutoring sessions: a student requests, the tutor accepts or declines.
#
# The matching engine only SUGGESTS tutors. Capacity is enforced here, when
# a tutor accepts. Every function re-checks roles against the database.

from datetime import date, datetime, timedelta

from services.auth_service import AuthError, PermissionDenied, require_role
from src.scheduling import ScheduleManager
from src.sets import SetOperations

ACTIVE = ("pending", "confirmed")


def _now():
    return datetime.now()


def _ends_at(row):
    return datetime.strptime(f"{row['session_date']} {row['end_time']}", "%Y-%m-%d %H:%M")


def upcoming_dates(day_name, weeks=4):
    """The next `weeks` calendar dates (after today) that fall on day_name."""
    names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
             "Saturday", "Sunday"]
    target = names.index(day_name)
    today = _now().date()
    first = today + timedelta(days=(target - today.weekday()) % 7 or 7)
    return [first + timedelta(weeks=i) for i in range(weeks)]


def common_slots(db, tutor_id, student_id, subject_code=None):
    """Weekly slots when both are free (same sets as TimeMatch)."""
    schedules = ScheduleManager(db)
    sets = SetOperations(db)
    allowed_codes = {subject_code} if subject_code else sets.get_student_needs(student_id)
    tutor_slots = [
        sl for sl in schedules.get_tutor_available_slots(tutor_id)
        if sl.get("subject_code") is None or sl.get("subject_code") in allowed_codes
    ]
    return sets.availability_intersection(
        schedules.get_student_free_slots(student_id),
        tutor_slots,
    )


def _people(db, student_id=None, tutor_id=None):
    """All profile ids belonging to the same person(s), for cross-role checks."""
    students, tutors = set(), set()
    for sid, tid in ((student_id, None), (None, tutor_id)):
        if sid is None and tid is None:
            continue
        row = db.fetch_one(
            "SELECT student_id, tutor_id FROM users "
            "WHERE student_id = ? OR tutor_id = ?", (sid, tid))
        if sid is not None:
            students.add(sid)
        if tid is not None:
            tutors.add(tid)
        if row:
            if row["student_id"] is not None:
                students.add(row["student_id"])
            if row["tutor_id"] is not None:
                tutors.add(row["tutor_id"])
    return students, tutors


def _is_busy(db, day, start, end, students, tutors, exclude_id=None):
    clauses, params = [], [day, end, start, exclude_id or -1]
    if students:
        clauses.append(f"student_id IN ({','.join('?' * len(students))})")
        params += list(students)
    if tutors:
        clauses.append(f"tutor_id IN ({','.join('?' * len(tutors))})")
        params += list(tutors)
    row = db.fetch_one(
        "SELECT 1 FROM sessions WHERE status IN ('pending','confirmed') "
        "AND session_date = ? AND start_time < ? AND end_time > ? "
        f"AND session_id != ? AND ({' OR '.join(clauses)})",
        tuple(params),
    )
    return row is not None


# ------------------------------------------------------------- request
def request_session(db, user_id, tutor_id, subject_id, session_date,
                    start, end, note=""):
    user = require_role(db, user_id, "student")
    student_id = user["student_id"]

    tutor = db.fetch_one("SELECT verified FROM tutors WHERE tutor_id = ?", (tutor_id,))
    if tutor is None or not tutor["verified"]:
        raise AuthError("That tutor is not available.")
    if user["tutor_id"] == tutor_id:
        raise AuthError("You cannot request a session with yourself.")
    if not db.fetch_one("SELECT 1 FROM tutor_subjects WHERE tutor_id=? AND subject_id=?",
                        (tutor_id, subject_id)):
        raise AuthError("This tutor does not teach that subject.")
    if not db.fetch_one("SELECT 1 FROM student_subjects WHERE student_id=? AND subject_id=?",
                        (student_id, subject_id)):
        raise AuthError("Add this class to your list first.")

    try:
        day = datetime.strptime(session_date, "%Y-%m-%d").date()
    except ValueError as error:
        raise AuthError("Choose a valid date.") from error
    if day <= _now().date():
        raise AuthError("Choose a date in the future.")
    if start >= end:
        raise AuthError("The start time must be before the end time.")
    if (datetime.strptime(end, "%H:%M") - datetime.strptime(start, "%H:%M")
            < timedelta(minutes=30)):
        raise AuthError("A session must last at least 30 minutes.")

    day_name = day.strftime("%A")
    if not any(s["day"] == day_name and s["start_time"] <= start and end <= s["end_time"]
               for s in common_slots(db, tutor_id, student_id)):
        raise AuthError("That time is outside the hours you are both free.")

    if db.fetch_one(
        "SELECT 1 FROM sessions WHERE student_id=? AND subject_id=? "
        "AND status IN ('pending','confirmed') AND session_date >= ?",
        (student_id, subject_id, _now().date().isoformat())):
        raise AuthError("You already have an active request for this class.")

    students, tutors = _people(db, student_id=student_id, tutor_id=tutor_id)
    if _is_busy(db, session_date, start, end, students, tutors):
        raise AuthError("One of you already has a session at that time.")

    db.execute(
        "INSERT INTO sessions (student_id, tutor_id, subject_id, session_date, "
        "start_time, end_time, note) VALUES (?,?,?,?,?,?,?)",
        (student_id, tutor_id, subject_id, session_date, start, end,
         (note or "").strip()[:200] or None),
    )


# ------------------------------------------------------------- respond
def _owned(db, user_id, session_id, as_tutor):
    user = require_role(db, user_id, "tutor" if as_tutor else "student")
    row = db.fetch_one("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    mine = user["tutor_id"] if as_tutor else user["student_id"]
    key = "tutor_id" if as_tutor else "student_id"
    if row is None or row[key] != mine:
        raise PermissionDenied("You do not have access to this session.")
    return row


def respond(db, user_id, session_id, accept):
    row = _owned(db, user_id, session_id, as_tutor=True)
    if row["status"] != "pending":
        raise AuthError("This request has already been answered.")
    if _ends_at(row) <= _now():
        raise AuthError("This request has expired.")

    if not accept:
        db.execute("UPDATE sessions SET status='declined' WHERE session_id=?",
                   (session_id,))
        return

    tutor = db.fetch_one("SELECT capacity, verified FROM tutors WHERE tutor_id=?",
                         (row["tutor_id"],))
    if not tutor["verified"]:
        raise AuthError("Your tutor profile is not verified yet.")
    already = db.fetch_one(
        "SELECT 1 FROM sessions WHERE tutor_id=? AND student_id=? "
        "AND status='confirmed'", (row["tutor_id"], row["student_id"]))
    taken = db.fetch_one(
        "SELECT COUNT(DISTINCT student_id) AS n FROM sessions "
        "WHERE tutor_id=? AND status='confirmed'", (row["tutor_id"],))["n"]
    if not already and taken >= tutor["capacity"]:
        raise AuthError("You have no spots left. Your capacity is full.")

    students, tutors = _people(db, student_id=row["student_id"], tutor_id=row["tutor_id"])
    if _is_busy(db, row["session_date"], row["start_time"], row["end_time"],
                students, tutors, exclude_id=session_id):
        raise AuthError("A confirmed or pending session already uses that time.")
    db.execute("UPDATE sessions SET status='confirmed' WHERE session_id=?", (session_id,))


def cancel(db, user_id, session_id):
    user = require_role(db, user_id, "member")
    row = db.fetch_one("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    if row is None or (row["student_id"] != user["student_id"]
                       and row["tutor_id"] != user["tutor_id"]):
        raise PermissionDenied("You do not have access to this session.")
    if row["status"] not in ACTIVE or _ends_at(row) <= _now():
        raise AuthError("This session can no longer be cancelled.")
    db.execute("UPDATE sessions SET status='cancelled' WHERE session_id=?", (session_id,))


# ---------------------------------------------------------------- list
def list_sessions(db, user_id, mode):
    """Sessions for the user in 'Learning' or 'Tutoring' mode, by tab."""
    user = require_role(db, user_id, "student" if mode == "Learning" else "tutor")
    mine = user["student_id"] if mode == "Learning" else user["tutor_id"]
    column = "student_id" if mode == "Learning" else "tutor_id"

    rows = db.fetch_all(
        "SELECT x.*, s.name AS student_name, s.course AS student_course, "
        "t.name AS tutor_name, t.course AS tutor_course, "
        "sub.subject_name FROM sessions x "
        "JOIN students s ON s.student_id = x.student_id "
        "JOIN tutors t ON t.tutor_id = x.tutor_id "
        "JOIN subjects sub ON sub.subject_id = x.subject_id "
        f"WHERE x.{column} = ? ORDER BY x.session_date, x.start_time", (mine,))

    tabs = {"reply": [], "sent": [], "upcoming": [], "past": []}
    now = _now()
    for row in rows:
        row = dict(row)
        over = _ends_at(row) <= now
        if row["status"] == "pending" and not over:
            tabs["reply" if mode == "Tutoring" else "sent"].append(row)
        elif row["status"] == "confirmed" and not over:
            tabs["upcoming"].append(row)
        else:
            tabs["past"].append(row)
    return tabs
