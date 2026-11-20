import sqlite3
from datetime import timedelta

import pytest

from services import account_service as acct
from services import auth_service as auth
from services import session_service as sess
from services.auth_service import AuthError, PermissionDenied
from services.migrations import MIGRATION_1_USERS, SCHEMA_PATH, SEED_PATH, migrate
from src.database import Database
from src.logic import CompatibilityLogic
from src.relations import CompatibilityRelation
from src.scheduling import ScheduleManager
from src.sets import SetOperations


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setattr(auth, "BCRYPT_ROUNDS", 4)


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "p.db"
    con = sqlite3.connect(path)
    con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    con.executescript(SEED_PATH.read_text(encoding="utf-8"))
    con.commit(); con.close()
    d = Database(path); migrate(d); yield d; d.close()


def reg(db, email, role, name="Person"):
    return auth.register(db, name, email, "password-1", "password-1", role, 2, "BCS")


def logic(db):
    sets = SetOperations(db)
    return CompatibilityLogic(sets, ScheduleManager(db))


def mon_slot(db):
    """A future Monday date string."""
    return sess.upcoming_dates("Monday")[0].isoformat()


def setup_pair(db):
    """Student needs Discrete Structures (11); tutor teaches it, free Mon 10-12."""
    st = reg(db, "s@x.com", "student", "Stu")
    tu = reg(db, "t@x.com", "tutor", "Tut")
    for u, kind in ((st, "student"), (tu, "tutor")):
        acct.set_languages(db, u["user_id"], kind, ["English"])
    acct.add_need(db, st["user_id"], 11, "proofs")
    acct.add_teach(db, tu["user_id"], 11)
    acct.add_availability(db, tu["user_id"], "Monday", "10:00", "12:00")
    acct.set_tutor_verified(
        db, auth.create_admin(db, "a@x.com", "admin-password", "Admin")["user_id"],
        tu["tutor_id"], True)
    return st, tu


# ---- migration 2: old single-role accounts survive --------------------
def test_migration_2_converts_existing_accounts(tmp_path):
    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    con.executescript(SEED_PATH.read_text(encoding="utf-8"))
    con.executescript(MIGRATION_1_USERS)
    con.execute("INSERT INTO users (email,password_hash,role,student_id) "
                "VALUES ('old@x.com','h','student',1)")
    con.commit(); con.close()
    d = Database(path)
    assert migrate(d) == 3
    row = d.fetch_one("SELECT role, student_id FROM users WHERE email='old@x.com'")
    assert (row["role"], row["student_id"]) == ("member", 1)
    d.close()


# ---- dual role --------------------------------------------------------
def test_register_both_and_add_profile(db):
    both = reg(db, "b@x.com", "both")
    assert both["modes"] == ["Learning", "Tutoring"]
    only = reg(db, "o@x.com", "student")
    acct.add_profile(db, only["user_id"], "tutor")
    assert auth.get_user(db, only["user_id"])["modes"] == ["Learning", "Tutoring"]
    with pytest.raises(AuthError):
        acct.add_profile(db, only["user_id"], "tutor")


def test_person_is_never_matched_with_themselves(db):
    me = reg(db, "me@x.com", "both")
    acct.add_need(db, me["user_id"], 11)
    acct.add_teach(db, me["user_id"], 11)
    acct.set_languages(db, me["user_id"], "student", ["English"])
    acct.set_languages(db, me["user_id"], "tutor", ["English"])
    acct.add_availability(db, me["user_id"], "Monday", "10:00", "12:00")
    admin = auth.create_admin(db, "a@x.com", "admin-password", "Admin")
    acct.set_tutor_verified(db, admin["user_id"], me["tutor_id"], True)
    lg = logic(db)
    report = lg.evaluate(me["tutor_id"], me["student_id"])
    assert report["subject_match"] and report["time_match"] and report["language_match"]
    assert report["not_self"] is False and report["compatible"] is False


def test_only_verified_tutors_enter_the_relation(db):
    tu = reg(db, "t@x.com", "tutor")
    builder = CompatibilityRelation(logic(db))
    assert tu["tutor_id"] not in builder.get_tutors()
    admin = auth.create_admin(db, "a@x.com", "admin-password", "Admin")
    acct.set_tutor_verified(db, admin["user_id"], tu["tutor_id"], True)
    assert tu["tutor_id"] in builder.get_tutors()
    with pytest.raises(PermissionDenied):
        acct.set_tutor_verified(db, tu["user_id"], tu["tutor_id"], False)


# ---- schedules --------------------------------------------------------
def test_class_and_availability_validation(db):
    both = reg(db, "b@x.com", "both")
    uid = both["user_id"]
    acct.add_class(db, uid, 11, "Monday", "08:00", "10:00")
    with pytest.raises(AuthError, match="overlaps"):
        acct.add_class(db, uid, 11, "Monday", "09:00", "11:00")
    with pytest.raises(AuthError, match="before"):
        acct.add_class(db, uid, 11, "Tuesday", "10:00", "09:00")
    with pytest.raises(AuthError, match="Monday to Saturday"):
        acct.add_class(db, uid, 11, "Sunday", "08:00", "09:00")
    with pytest.raises(AuthError, match="own classes"):
        acct.add_availability(db, uid, "Monday", "09:00", "10:30")
    acct.add_availability(db, uid, "Monday", "10:00", "12:00")


def test_users_cannot_edit_each_others_schedules(db):
    a = reg(db, "a1@x.com", "student"); b = reg(db, "b1@x.com", "student")
    acct.add_class(db, a["user_id"], 11, "Monday", "08:00", "09:00")
    sid = db.fetch_one("SELECT schedule_id FROM student_schedule WHERE student_id=?",
                       (a["student_id"],))["schedule_id"]
    acct.delete_class(db, b["user_id"], sid)  # silently ignored: not b's row
    assert db.fetch_one("SELECT 1 FROM student_schedule WHERE schedule_id=?", (sid,))
    with pytest.raises(PermissionDenied):
        acct.add_availability(db, b["user_id"], "Monday", "10:00", "11:00")


# ---- sessions ---------------------------------------------------------
def test_request_accept_and_capacity(db):
    st, tu = setup_pair(db)
    day = mon_slot(db)
    sess.request_session(db, st["user_id"], tu["tutor_id"], 11, day, "10:00", "11:00", "hi")
    with pytest.raises(AuthError, match="active request"):
        sess.request_session(db, st["user_id"], tu["tutor_id"], 11, day, "11:00", "12:00")
    sid = sess.list_sessions(db, tu["user_id"], "Tutoring")["reply"][0]["session_id"]

    with pytest.raises(PermissionDenied):  # the student cannot answer it
        sess.respond(db, st["user_id"], sid, True)

    db.execute("UPDATE tutors SET capacity = 1 WHERE tutor_id = ?", (tu["tutor_id"],))
    sess.respond(db, tu["user_id"], sid, True)
    assert sess.list_sessions(db, st["user_id"], "Learning")["upcoming"]

    st2 = reg(db, "s2@x.com", "student", "Stu2")
    acct.set_languages(db, st2["user_id"], "student", ["English"])
    acct.add_need(db, st2["user_id"], 11)
    sess.request_session(db, st2["user_id"], tu["tutor_id"], 11,
                         (sess.upcoming_dates("Monday")[1]).isoformat(), "10:00", "11:00")
    sid2 = sess.list_sessions(db, tu["user_id"], "Tutoring")["reply"][0]["session_id"]
    with pytest.raises(AuthError, match="no spots"):
        sess.respond(db, tu["user_id"], sid2, True)  # capacity enforced here


def test_request_validation(db):
    st, tu = setup_pair(db)
    day = mon_slot(db)
    with pytest.raises(AuthError, match="outside the hours"):
        sess.request_session(db, st["user_id"], tu["tutor_id"], 11, day, "13:00", "14:00")
    with pytest.raises(AuthError, match="future"):
        sess.request_session(db, st["user_id"], tu["tutor_id"], 11, "2020-01-06", "10:00", "11:00")
    with pytest.raises(AuthError, match="does not teach"):
        sess.request_session(db, st["user_id"], tu["tutor_id"], 4, day, "10:00", "11:00")
    with pytest.raises(AuthError, match="30 minutes"):
        sess.request_session(db, st["user_id"], tu["tutor_id"], 11, day, "10:00", "10:15")
    with pytest.raises(PermissionDenied):  # a tutor-only account cannot request
        sess.request_session(db, tu["user_id"], tu["tutor_id"], 11, day, "10:00", "11:00")


def test_cannot_request_yourself_and_cancel_rules(db):
    both = reg(db, "b@x.com", "both")
    acct.add_need(db, both["user_id"], 11); acct.add_teach(db, both["user_id"], 11)
    admin = auth.create_admin(db, "a0@x.com", "admin-password", "Admin0")
    acct.set_tutor_verified(db, admin["user_id"], both["tutor_id"], True)
    with pytest.raises(AuthError, match="yourself"):
        sess.request_session(db, both["user_id"], both["tutor_id"], 11,
                             mon_slot(db), "10:00", "11:00")

    st, tu = setup_pair(db)
    sess.request_session(db, st["user_id"], tu["tutor_id"], 11, mon_slot(db), "10:00", "11:00")
    sid = sess.list_sessions(db, st["user_id"], "Learning")["sent"][0]["session_id"]
    outsider = reg(db, "o@x.com", "student")
    with pytest.raises(PermissionDenied):
        sess.cancel(db, outsider["user_id"], sid)
    sess.cancel(db, st["user_id"], sid)
    assert sess.list_sessions(db, st["user_id"], "Learning")["past"]


# ---- accounts for existing (seed) profiles ----------------------------
def test_create_account_for_seed_profile(db):
    user = auth.create_account_for_profile(db, "student.a@tugma.demo",
                                           "demo-password", student_id=1)
    assert user["name"] == "Student A" and user["modes"] == ["Learning"]
    assert auth.login(db, "student.a@tugma.demo", "demo-password")["student_id"] == 1
    with pytest.raises(AuthError):  # that profile already has a login
        auth.create_account_for_profile(db, "other@tugma.demo", "demo-password", student_id=1)
    with pytest.raises(AuthError, match="does not exist"):
        auth.create_account_for_profile(db, "x@tugma.demo", "demo-password", tutor_id=99)
