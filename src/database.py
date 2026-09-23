# Handles all communication between the Python application and SQLite.

import sqlite3
from pathlib import Path


class Database:
    # Manages SQLite database connections and transactions.

    def __init__(self, db_path=None):
        if db_path is None:
            project_root = Path(__file__).resolve().parent.parent
            db_path = project_root / "database" / "tugma.db"
            print(db_path)

        self.db_path = Path(db_path)
        self.connection = None

    def connect(self):
        """Connect to the SQLite database."""
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA foreign_keys = ON")

        return self.connection

    def execute(self, query, parameters=None):
        """Execute INSERT, UPDATE, DELETE, or other non-SELECT queries."""
        connection = self.connect()

        if parameters is None:
            parameters = ()

        cursor = connection.execute(query, parameters)
        connection.commit()

        return cursor

    def fetch_one(self, query, parameters=None):
        """Execute a SELECT query and return one row."""
        connection = self.connect()

        if parameters is None:
            parameters = ()

        cursor = connection.execute(query, parameters)

        return cursor.fetchone()

    def fetch_all(self, query, parameters=None):
        """Execute a SELECT query and return all rows."""
        connection = self.connect()

        if parameters is None:
            parameters = ()

        cursor = connection.execute(query, parameters)

        return cursor.fetchall()

    def close(self):
        """Close the database connection."""
        if self.connection is not None:
            self.connection.close()
            self.connection = None
