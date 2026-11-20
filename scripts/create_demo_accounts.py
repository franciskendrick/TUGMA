# Gives every seed student and tutor (Student A, Tutor C, ...) a login so you
# can test the portal as that person. Run from the repository root:
#
#     python -m scripts.create_demo_accounts
#
# All demo accounts share ONE password that you type at a hidden prompt (or
# set in the TUGMA_DEMO_PASSWORD environment variable). Emails look like
# student.a@tugma.demo and tutor.c@tugma.demo. Accounts that already exist
# are skipped. For testing only: do not use this on a real deployment.

import getpass
import os
import re
import sys

from services.auth_service import AuthError, create_account_for_profile
from services.migrations import DB_PATH, ensure_database
from src.database import Database


def email_for(name):
    slug = re.sub(r"[^a-z0-9]+", ".", name.lower()).strip(".")
    return f"{slug}@tugma.demo"


def main():
    ensure_database()
    password = os.environ.get("TUGMA_DEMO_PASSWORD") or getpass.getpass(
        "Shared demo password (8+ characters): "
    )

    db = Database(DB_PATH)
    created = []
    try:
        people = [
            ("Student", r["student_id"], r["name"])
            for r in db.fetch_all("SELECT student_id, name FROM students ORDER BY student_id")
            if not db.fetch_one("SELECT 1 FROM users WHERE student_id = ?", (r["student_id"],))
        ] + [
            ("Tutor", r["tutor_id"], r["name"])
            for r in db.fetch_all("SELECT tutor_id, name FROM tutors ORDER BY tutor_id")
            if not db.fetch_one("SELECT 1 FROM users WHERE tutor_id = ?", (r["tutor_id"],))
        ]

        for kind, profile_id, name in people:
            email = email_for(name)
            try:
                create_account_for_profile(
                    db,
                    email,
                    password,
                    student_id=profile_id if kind == "Student" else None,
                    tutor_id=profile_id if kind == "Tutor" else None,
                )
                created.append((name, email))
            except AuthError as error:
                sys.exit(f"{name}: {error}")
    finally:
        db.close()

    if not created:
        print("Every student and tutor already has an account.")
    for name, email in created:
        print(f"{name:12} {email}")


if __name__ == "__main__":
    main()
