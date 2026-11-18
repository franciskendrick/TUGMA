import sqlite3
import pytest

from services import auth_service as auth
from services.auth_service import AuthError, PermissionDenied
from services.migrations import SCHEMA_PATH, SEED_PATH, migrate
from src.database import Database


@pytest.fixture(autouse=True)
def fast_bcrypt(monkeypatch):
    monkeypatch.setattr(auth, "BCRYPT_ROUNDS", 4)


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "test.db"
    con = sqlite3.connect(path)
    con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    con.executescript(SEED_PATH.read_text(encoding="utf-8"))
    con.commit()
    con.close()
    database = Database(path)
    migrate(database)
    yield database
    database.close()


def count(db, table):
    return db.fetch_one(f"SELECT COUNT(*) AS n FROM {table}")["n"]


def reg(db, **kw):
    args = dict(full_name="Ana Cruz", email="ana@example.com",
                password="correct-horse", confirm_password="correct-horse",
                role="student", grade_level=2, course="BCS")
    args.update(kw)
    return auth.register(db, **args)


# ---- migration -------------------------------------------------------
def test_migration_is_idempotent_and_preserves_seed(tmp_path):
    path = tmp_path / "m.db"
    con = sqlite3.connect(path)
    con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    con.executescript(SEED_PATH.read_text(encoding="utf-8"))
    con.commit(); con.close()

    database = Database(path)
    before = {t: count(database, t) for t in
              ("students", "tutors", "subjects", "student_schedule",
               "tutor_availability")}
    assert migrate(database) == 1
    assert migrate(database) == 1  # second run changes nothing
    after = {t: count(database, t) for t in before}
    assert before == after
    assert before["students"] == 7 and before["tutors"] == 5
    database.close()


# ---- registration ----------------------------------------------------
def test_register_student_creates_profile_and_account(db):
    user = reg(db)
    assert user["role"] == "student" and user["student_id"] is not None
    assert user["name"] == "Ana Cruz"
    assert count(db, "students") == 8


def test_register_tutor_starts_unverified(db):
    user = reg(db, email="t@example.com", role="tutor")
    row = db.fetch_one("SELECT verified FROM tutors WHERE tutor_id = ?",
                       (user["tutor_id"],))
    assert row["verified"] == 0


def test_duplicate_email_is_case_insensitive_and_leaves_no_orphan(db):
    reg(db)
    students_before = count(db, "students")
    with pytest.raises(AuthError, match="already exists"):
        reg(db, email="ANA@Example.com", full_name="Someone Else")
    assert count(db, "students") == students_before  # rolled back


@pytest.mark.parametrize("kw,msg", [
    (dict(confirm_password="different"), "do not match"),
    (dict(password="short", confirm_password="short"), "at least"),
    (dict(password="x" * 73, confirm_password="x" * 73), "too long"),
    (dict(email="not-an-email"), "valid email"),
    (dict(full_name="  "), "full name"),
    (dict(grade_level=0), "Year level"),
    (dict(role="admin"), "Only student and tutor"),
])
def test_register_validation(db, kw, msg):
    with pytest.raises(AuthError, match=msg):
        reg(db, **kw)
    assert count(db, "users") == 0


def test_password_is_never_stored_in_plaintext(db):
    reg(db)
    stored = db.fetch_one("SELECT password_hash FROM users")["password_hash"]
    assert "correct-horse" not in stored and stored.startswith("$2")


# ---- login -----------------------------------------------------------
def test_login_success_and_failures(db):
    reg(db)
    assert auth.login(db, " ANA@example.com ", "correct-horse")["role"] == "student"
    with pytest.raises(AuthError, match="Invalid email or password"):
        auth.login(db, "ana@example.com", "wrong-password")
    with pytest.raises(AuthError, match="Invalid email or password"):
        auth.login(db, "nobody@example.com", "whatever123")


def test_disabled_account_cannot_log_in_or_pass_get_user(db):
    user = reg(db)
    db.execute("UPDATE users SET is_active = 0 WHERE user_id = ?",
               (user["user_id"],))
    with pytest.raises(AuthError, match="disabled"):
        auth.login(db, "ana@example.com", "correct-horse")
    assert auth.get_user(db, user["user_id"]) is None


# ---- authorization ---------------------------------------------------
def test_admin_creation_and_role_checks(db):
    admin = auth.create_admin(db, "admin@example.com", "admin-password", "Admin")
    student = reg(db)
    tutor = reg(db, email="t@example.com", role="tutor", full_name="Tom")

    assert auth.require_role(db, admin["user_id"], "admin")["role"] == "admin"
    with pytest.raises(PermissionDenied):
        auth.require_role(db, student["user_id"], "admin")
    with pytest.raises(PermissionDenied):
        auth.require_role(db, tutor["user_id"], "admin")
    with pytest.raises(PermissionDenied):
        auth.require_role(db, 9999, "admin")


def test_database_rejects_inconsistent_role_profile_links(db):
    with pytest.raises(sqlite3.IntegrityError):  # student without a profile
        db.execute("INSERT INTO users (email,password_hash,role) "
                   "VALUES ('a@b.co','x','student')")
    with pytest.raises(sqlite3.IntegrityError):  # admin with a profile
        db.execute("INSERT INTO users (email,password_hash,role,student_id,"
                   "display_name) VALUES ('c@d.co','x','admin',1,'A')")
    with pytest.raises(sqlite3.IntegrityError):  # student pointing at a tutor
        db.execute("INSERT INTO users (email,password_hash,role,student_id,"
                   "tutor_id) VALUES ('e@f.co','x','student',1,1)")


def test_deleting_a_profile_removes_its_account(db):
    user = reg(db)
    db.execute("DELETE FROM students WHERE student_id = ?", (user["student_id"],))
    assert count(db, "users") == 0


# ---- account management ---------------------------------------------
def test_only_admins_can_list_or_disable_accounts(db):
    admin = auth.create_admin(db, "admin@example.com", "admin-password", "Admin")
    student = reg(db)

    assert len(auth.list_accounts(db, admin["user_id"])) == 2
    with pytest.raises(PermissionDenied):
        auth.list_accounts(db, student["user_id"])
    with pytest.raises(PermissionDenied):
        auth.set_account_active(db, student["user_id"], admin["user_id"], False)

    auth.set_account_active(db, admin["user_id"], student["user_id"], False)
    with pytest.raises(AuthError, match="disabled"):
        auth.login(db, "ana@example.com", "correct-horse")
    auth.set_account_active(db, admin["user_id"], student["user_id"], True)
    assert auth.login(db, "ana@example.com", "correct-horse")["role"] == "student"


def test_admin_cannot_disable_self(db):
    admin = auth.create_admin(db, "admin@example.com", "admin-password", "Admin")
    with pytest.raises(AuthError, match="own account"):
        auth.set_account_active(db, admin["user_id"], admin["user_id"], False)