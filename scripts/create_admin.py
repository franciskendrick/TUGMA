# Creates an administrator account. Run from the repository root:
#
#     python -m scripts.create_admin
#
# The password is typed at a hidden prompt; nothing is hardcoded.

import getpass
import sys

from services.auth_service import AuthError, create_admin
from services.migrations import DB_PATH, ensure_database
from src.database import Database


def main():
    ensure_database()

    email = "admin@gmail.com"
    name = "admin"
    password = "adminpassword"

    db = Database(DB_PATH)
    try:
        user = create_admin(db, email, password, name)
    except AuthError as error:
        sys.exit(str(error))
    finally:
        db.close()

    print(f"Administrator created: {user['email']}")


if __name__ == "__main__":
    main()
