# Shared pipeline + presentation helpers (used by the admin portal and the
# student/tutor portal). Coordinates src/; contains no matching logic.

# Main entry point for the TUGMA Streamlit web application.
# Handles the user interface and coordinates the different system components.
#
# This file contains NO mathematical logic. Every step of the pipeline
#   Data -> Sets -> Logic -> Relation -> Graph -> Matching
# is delegated to the corresponding module in src/.

import sqlite3
from collections import Counter
from datetime import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from services.auth_service import (
    AuthError,
    PermissionDenied,
    get_user,
    list_accounts,
    require_role,
    set_account_active,
)
from services.migrations import DB_PATH, ensure_database
from src.database import Database
from src.sets import SetOperations
from src.scheduling import ScheduleManager
from src.logic import CompatibilityLogic
from src.relations import CompatibilityRelation
from src.graph import BipartiteGraph
from src.matching import CapacityMatcher
from src.visualization import TUGMAVisualizer


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
LANGUAGES = ["Filipino", "English"]


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def fmt_time(value):
    """Format a time object or HH:MM string as HH:MM."""
    return value if isinstance(value, str) else value.strftime("%H:%M")


def fmt_slot(slot):
    return (
        f"{slot['day'][:3]} "
        f"{fmt_time(slot['start_time'])}–{fmt_time(slot['end_time'])}"
    )


def slots_to_df(slots):
    return pd.DataFrame(
        [
            {
                "Day": s["day"],
                "Start": fmt_time(s["start_time"]),
                "End": fmt_time(s["end_time"]),
            }
            for s in slots
        ],
        columns=["Day", "Start", "End"],
    )


class Services:
    """Bundles the src/ components around ONE shared database connection.

    Connections are created per run and closed afterwards, because
    Streamlit may execute reruns on different threads.
    """

    def __init__(self):
        self.db = Database(DB_PATH)
        self.sets = SetOperations(self.db)
        self.schedules = ScheduleManager(self.db)
        self.logic = CompatibilityLogic(self.sets, self.schedules)

    def close(self):
        self.logic.close()


# ----------------------------------------------------------------------
# Pipeline: Data -> Sets -> Logic -> Relation -> Graph -> Matching
# ----------------------------------------------------------------------
@st.cache_data(show_spinner="Running the TUGMA pipeline...")
def run_pipeline(db_mtime, capacity_mode, uniform_capacity):
    """Run the full pipeline. `db_mtime` only invalidates the cache."""
    svc = Services()

    try:
        builder = CompatibilityRelation(svc.logic)
        tutor_ids = builder.get_tutors()
        student_ids = builder.get_students()

        tutor_rows = svc.db.fetch_all(
            "SELECT tutor_id, name, grade_level, course, verified, capacity "
            "FROM tutors ORDER BY tutor_id"
        )
        student_rows = svc.db.fetch_all(
            "SELECT student_id, name, grade_level, course "
            "FROM students ORDER BY student_id"
        )

        # Set Theory: Subjects(t), Needs(s), languages
        tutors_df = pd.DataFrame(
            [
                {
                    "tutor_id": r["tutor_id"],
                    "name": r["name"],
                    "year": r["grade_level"],
                    "course": r["course"],
                    "verified": bool(r["verified"]),
                    "capacity": r["capacity"],
                    "subjects": ", ".join(
                        sorted(svc.sets.get_tutor_subjects(r["tutor_id"]))
                    ),
                    "languages": ", ".join(
                        sorted(svc.sets.get_tutor_languages(r["tutor_id"]))
                    ),
                }
                for r in tutor_rows
            ]
        )
        students_df = pd.DataFrame(
            [
                {
                    "student_id": r["student_id"],
                    "name": r["name"],
                    "year": r["grade_level"],
                    "course": r["course"],
                    "needs": ", ".join(
                        sorted(svc.sets.get_student_needs(r["student_id"]))
                    ),
                    "languages": ", ".join(
                        sorted(svc.sets.get_student_languages(r["student_id"]))
                    ),
                }
                for r in student_rows
            ]
        )

        # Predicate Logic: every pair in T x S, with explanations
        reports = [
            svc.logic.evaluate(t, s) for t in tutor_ids for s in student_ids
        ]

        # Relation R = {(t, s) | Compatible(t, s)}
        relation = builder.construct_relation()

        # Graph G = (T u S, E)
        graph_builder = BipartiteGraph()
        graph = graph_builder.create_graph(tutor_ids, student_ids, relation)
        verification = graph_builder.verify_graph()

        # Tutor capacity policy
        if capacity_mode == "uniform":
            capacities = {t: uniform_capacity for t in tutor_ids}
        else:
            capacities = {r["tutor_id"]: r["capacity"] for r in tutor_rows}

        # Capacity-constrained matching
        if tutor_ids and student_ids:
            matcher = CapacityMatcher(graph, capacities)
            pairs = matcher.find_matching()
            unmatched_ids = matcher.get_unmatched_students()
            remaining = matcher.get_remaining_capacity()
        else:
            pairs, unmatched_ids = [], list(student_ids)
            remaining = dict(capacities)

        # Presentation details for each selected edge
        matches = []
        for t, s in sorted(pairs, key=lambda p: (p[1], p[0])):
            shared = svc.sets.subject_intersection(
                svc.sets.get_tutor_subjects(t),
                svc.sets.get_student_needs(s),
            )
            slots = svc.sets.availability_intersection(
                svc.schedules.get_student_free_slots(s),
                svc.schedules.get_tutor_available_slots(t),
            )
            matches.append(
                {"student_id": s, "tutor_id": t,
                 "shared": sorted(shared), "slots": slots}
            )

        compatible_count = Counter(s for _, s in relation)
        unmatched = [
            {"student_id": s, "has_compatible": compatible_count[s] > 0}
            for s in unmatched_ids
        ]
        subject_names = {
            r["subject_code"]: r["subject_name"].title()
            for r in svc.db.fetch_all(
                "SELECT subject_code, subject_name FROM subjects"
            )
        }

        return {
            "tutor_ids": tutor_ids,
            "student_ids": student_ids,
            "tutors": tutors_df,
            "students": students_df,
            "reports": reports,
            "relation": relation,
            "graph": graph,
            "verification": verification,
            "capacities": capacities,
            "pairs": pairs,
            "matches": matches,
            "unmatched": unmatched,
            "remaining": remaining,
            "subject_names": subject_names,
        }
    finally:
        svc.close()


SUBJECT_HINT = "Subjects"


def fmt12(value):
    """'14:30' or time -> '2:30 PM'."""
    if isinstance(value, str):
        hour, minute = map(int, value.split(":"))
    else:
        hour, minute = value.hour, value.minute
    suffix = "AM" if hour < 12 else "PM"
    return f"{(hour % 12) or 12}:{minute:02d} {suffix}"


def fmt_range(slot):
    return (
        f"{slot['day'][:3]} {fmt12(slot['start_time'])}"
        f"–{fmt12(slot['end_time'])}"
    )


def to_minutes(value):
    if isinstance(value, str):
        hour, minute = map(int, value.split(":"))
        return hour * 60 + minute
    return value.hour * 60 + value.minute


def timetable(blocks, label):
    """Weekly grid (30-minute rows, Mon–Sat) as a styled table.

    blocks: dicts with day, start_time, end_time and optional 'text'.
    """
    rows = range(7 * 60, 17 * 60, 30)
    grid = {
        day: [
            next(
                (
                    b.get("text", label)
                    for b in blocks
                    if b["day"] == day
                    and to_minutes(b["start_time"]) < start + 30
                    and to_minutes(b["end_time"]) > start
                ),
                "",
            )
            for start in rows
        ]
        for day in DAYS
    }
    df = pd.DataFrame(
        grid, index=[fmt12(f"{m // 60}:{m % 60:02d}") for m in rows]
    )

    def color(cell):
        if not cell:
            return ""
        if cell == "Session":
            return "background-color: #dbeafe; color: #1e3a8a"
        if cell in ("Free", "Available"):
            return "background-color: #d9f2e3; color: #14532d"
        return "background-color: #fde2e2; color: #7f1d1d"

    styler = df.style
    return (getattr(styler, "map", None) or styler.applymap)(color)


