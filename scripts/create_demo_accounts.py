# Gives every seed student and tutor a login so you can test the portal as
# that person. Run from the repository root:
#
#     python -m scripts.create_demo_accounts
#
# Every demo account uses the password "demopassword" (override it with the
# TUGMA_DEMO_PASSWORD environment variable). Emails are the person's name,
# for example angelo.bautista@tugma.demo. Accounts that already exist are skipped.
#
# FOR LOCAL TESTING ONLY: the password is public, so never run this on a
# database that is reachable by other people.

import os
import re
import sys

from services.auth_service import AuthError, create_account_for_profile, hash_password
from services.migrations import DB_PATH, ensure_database
from src.database import Database

DEMO_PASSWORD = os.environ.get("TUGMA_DEMO_PASSWORD", "demopassword")


def email_for(name):
    slug = re.sub(r"[^a-z0-9]+", ".", name.lower()).strip(".")
    return f"{slug}@tugma.demo"


def main():
    ensure_database()
    password_hash = hash_password(DEMO_PASSWORD)  # hashed once, reused for every account

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
            try:
                create_account_for_profile(
                    db,
                    email_for(name),
                    DEMO_PASSWORD,
                    student_id=profile_id if kind == "Student" else None,
                    tutor_id=profile_id if kind == "Tutor" else None,
                    password_hash=password_hash,
                )
                created.append((kind, name, email_for(name)))
            except AuthError as error:
                sys.exit(f"{name}: {error}")
    finally:
        db.close()

    if not created:
        print("Every student and tutor already has an account.")
        return
    for kind, name, email in created:
        print(f"{kind:8} {name:28} {email}")
    print(f"\n{len(created)} accounts created. Password for all: {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()