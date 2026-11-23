# Registration, login, password hashing, and role authorization.
#
# Passwords are hashed with bcrypt and never stored in plaintext.
# Public registration can only create student and tutor accounts;
# administrator accounts come from create_admin() (scripts/create_admin.py).

import re
import sqlite3

import bcrypt

BCRYPT_ROUNDS = 12
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # bcrypt ignores/rejects anything longer
PUBLIC_ROLES = ("student", "tutor", "both")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthError(Exception):
    """A problem the user can fix; the message is safe to display."""


class PermissionDenied(Exception):
    """The caller's role does not allow the requested operation."""


# ---------------------------------------------------------------- hashing
def hash_password(password):
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("ascii")


def verify_password(password, password_hash):
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("ascii"))
    except ValueError:
        return False


# Used so a login for an unknown email costs the same as a real one.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


# ------------------------------------------------------------- validation
def normalize_email(email):
    return (email or "").strip().lower()


def _validate_email(email):
    if not EMAIL_PATTERN.match(email) or len(email) > 254:
        raise AuthError("Enter a valid email address.")


def _validate_password(password, confirm):
    if password != confirm:
        raise AuthError("The passwords do not match.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(
            f"The password must be at least {MIN_PASSWORD_LENGTH} characters."
        )
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise AuthError("The password is too long (72 bytes maximum).")


# ----------------------------------------------------------------- lookup
_USER_QUERY = """
    SELECT u.user_id, u.email, u.role, u.student_id, u.tutor_id,
           u.is_active, u.password_hash,
           COALESCE(s.name, t.name, u.display_name, u.email) AS name
    FROM users u
    LEFT JOIN students s ON s.student_id = u.student_id
    LEFT JOIN tutors   t ON t.tutor_id   = u.tutor_id
"""


def _session_dict(row):
    modes = []
    if row["student_id"] is not None:
        modes.append("Learning")
    if row["tutor_id"] is not None:
        modes.append("Tutoring")

    return {
        "user_id": row["user_id"],
        "email": row["email"],
        "role": row["role"],  # 'member' or 'admin'
        "student_id": row["student_id"],
        "tutor_id": row["tutor_id"],
        "modes": modes,
        "name": row["name"],
    }


def get_user(db, user_id):
    """Return the ACTIVE user with this id, or None."""
    row = db.fetch_one(_USER_QUERY + " WHERE u.user_id = ?", (user_id,))
    if row is None or not row["is_active"]:
        return None
    return _session_dict(row)


def require_role(db, user_id, *roles):
    """Verify against the database (not the session) that the user may act.

    roles may contain 'admin', 'member', 'student' (has a student profile)
    or 'tutor' (has a tutor profile).
    """
    user = get_user(db, user_id)
    allowed = user is not None and (
        user["role"] in roles
        or ("student" in roles and user["student_id"] is not None)
        or ("tutor" in roles and user["tutor_id"] is not None)
    )
    if not allowed:
        raise PermissionDenied("You do not have access to this operation.")
    return user


# ----------------------------------------------------------- registration
def register(db, full_name, email, password, confirm_password,
             role, grade_level, course):
    """Create a student or tutor profile and its account in ONE transaction."""
    if role not in PUBLIC_ROLES:
        raise AuthError("Only student and tutor accounts can be registered.")

    full_name = (full_name or "").strip()
    course = (course or "").strip()
    email = normalize_email(email)

    if not full_name or len(full_name) > 100:
        raise AuthError("Enter your full name (100 characters maximum).")
    if not course or len(course) > 50:
        raise AuthError("Enter your course (50 characters maximum).")
    if not isinstance(grade_level, int) or not 1 <= grade_level <= 6:
        raise AuthError("Year level must be between 1 and 6.")
    _validate_email(email)
    _validate_password(password, confirm_password)

    password_hash = hash_password(password)
    connection = db.connect()

    try:
        student_id = tutor_id = None
        if role in ("student", "both"):
            cursor = connection.execute(
                "INSERT INTO students (name, grade_level, course) "
                "VALUES (?, ?, ?)",
                (full_name, grade_level, course),
            )
            student_id = cursor.lastrowid
        if role in ("tutor", "both"):
            # New tutors are unverified until an administrator approves them.
            cursor = connection.execute(
                "INSERT INTO tutors (name, grade_level, course, verified) "
                "VALUES (?, ?, ?, 0)",
                (full_name, grade_level, course),
            )
            tutor_id = cursor.lastrowid

        cursor = connection.execute(
            "INSERT INTO users (email, password_hash, role, student_id, tutor_id) "
            "VALUES (?, ?, 'member', ?, ?)",
            (email, password_hash, student_id, tutor_id),
        )
        user_id = cursor.lastrowid
        connection.commit()
    except sqlite3.IntegrityError as error:
        connection.rollback()  # also removes the profile row just inserted
        if "users.email" in str(error):
            raise AuthError("An account with this email already exists.")
        raise AuthError("The account could not be created.") from error
    except Exception:
        connection.rollback()
        raise

    return get_user(db, user_id)


def create_admin(db, email, password, display_name):
    """Create an administrator. Not reachable from the public UI."""
    email = normalize_email(email)
    display_name = (display_name or "").strip()

    if not display_name:
        raise AuthError("Enter a display name.")
    _validate_email(email)
    _validate_password(password, password)

    try:
        cursor = db.execute(
            "INSERT INTO users (email, password_hash, role, display_name) "
            "VALUES (?, ?, 'admin', ?)",
            (email, hash_password(password), display_name),
        )
    except sqlite3.IntegrityError as error:
        raise AuthError("An account with this email already exists.") from error

    return get_user(db, cursor.lastrowid)


# ------------------------------------------------------------------ login
def login(db, email, password):
    """Return the session dict for valid credentials, else raise AuthError."""
    row = db.fetch_one(
        _USER_QUERY + " WHERE u.email = ?", (normalize_email(email),)
    )

    if row is None:
        verify_password(password or "", _DUMMY_HASH)
        raise AuthError("Invalid email or password.")

    if not verify_password(password or "", row["password_hash"]):
        raise AuthError("Invalid email or password.")

    if not row["is_active"]:
        raise AuthError("This account is disabled. Contact an administrator.")

    return _session_dict(row)


# ------------------------------------------------------- account management
def list_accounts(db, admin_user_id):
    """All accounts. Administrators only."""
    require_role(db, admin_user_id, "admin")
    rows = db.fetch_all(
        _USER_QUERY + " ORDER BY u.created_at, u.user_id"
    )
    return [
        {**_session_dict(r), "is_active": bool(r["is_active"])} for r in rows
    ]


def set_account_active(db, admin_user_id, target_user_id, active):
    """Enable or disable an account. Administrators only; not your own."""
    require_role(db, admin_user_id, "admin")
    if target_user_id == admin_user_id:
        raise AuthError("You cannot disable your own account.")
    cursor = db.execute(
        "UPDATE users SET is_active = ? WHERE user_id = ?",
        (1 if active else 0, target_user_id),
    )
    if cursor.rowcount == 0:
        raise AuthError("That account does not exist.")


def create_account_for_profile(db, email, password, student_id=None, tutor_id=None,
                               password_hash=None):
    """Give an EXISTING student and/or tutor profile a login (setup scripts).

    password_hash may be passed to reuse one bcrypt hash for many accounts."""
    email = normalize_email(email)
    _validate_email(email)
    _validate_password(password, password)

    if student_id is None and tutor_id is None:
        raise AuthError("Choose a student or tutor profile.")
    if student_id is not None and not db.fetch_one(
        "SELECT 1 FROM students WHERE student_id = ?", (student_id,)
    ):
        raise AuthError("That student profile does not exist.")
    if tutor_id is not None and not db.fetch_one(
        "SELECT 1 FROM tutors WHERE tutor_id = ?", (tutor_id,)
    ):
        raise AuthError("That tutor profile does not exist.")

    try:
        cursor = db.execute(
            "INSERT INTO users (email, password_hash, role, student_id, tutor_id) "
            "VALUES (?, ?, 'member', ?, ?)",
            (email, password_hash or hash_password(password), student_id, tutor_id),
        )
    except sqlite3.IntegrityError as error:
        raise AuthError(
            "That email is taken, or the profile already has an account."
        ) from error

    return get_user(db, cursor.lastrowid)