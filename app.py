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

from services.auth_service import PermissionDenied, get_user, require_role
from services.migrations import DB_PATH, ensure_database
from views.auth import render_auth
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


def reset_database(admin_user_id):
    """Restore the seed data. Administrator accounts are kept."""
    db = Database(DB_PATH)
    try:
        require_role(db, admin_user_id, "admin")  # re-checked server-side
        admins = [
            tuple(r)
            for r in db.fetch_all(
                "SELECT email, password_hash, display_name "
                "FROM users WHERE role = 'admin'"
            )
        ]
    finally:
        db.close()

    DB_PATH.unlink()
    ensure_database()

    db = Database(DB_PATH)
    try:
        for admin in admins:
            db.execute(
                "INSERT INTO users (email, password_hash, role, display_name) "
                "VALUES (?, ?, 'admin', ?)",
                admin,
            )
    finally:
        db.close()


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
                {
                    "Student": f"S{s}",
                    "Tutor": f"T{t}",
                    "Shared subject(s)": ", ".join(sorted(shared)),
                    "Possible sessions": "; ".join(fmt_slot(x) for x in slots),
                }
            )

        compatible_count = Counter(s for _, s in relation)
        unmatched = [
            {
                "Student": f"S{s}",
                "Reason": (
                    "No compatible tutor"
                    if compatible_count[s] == 0
                    else "All compatible tutors are at capacity"
                ),
            }
            for s in unmatched_ids
        ]

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
        }
    finally:
        svc.close()


# ----------------------------------------------------------------------
# Application
# ----------------------------------------------------------------------
class TUGMAApp:
    """Controls the overall Streamlit application."""

    def render(self, admin_user_id):
        self.admin_user_id = admin_user_id

        st.title("TUGMA")
        st.caption(
            "Tutor-Student Unified Graph-based Matching Approach — "
            "peer tutoring matches built from sets, logic, relations, "
            "and graphs."
        )

        capacity_mode, uniform_capacity = self.render_sidebar()

        data = run_pipeline(
            DB_PATH.stat().st_mtime_ns, capacity_mode, uniform_capacity
        )

        if not data["tutor_ids"] or not data["student_ids"]:
            st.warning(
                "The database needs at least one tutor and one student. "
                "Add them in the Manage data tab."
            )

        tabs = st.tabs(
            [
                "Results",
                "Data and schedules",
                "Compatibility",
                "Graph and matching",
                "Manage data",
            ]
        )

        with tabs[0]:
            self.render_results(data)
        with tabs[1]:
            self.render_data(data)
        with tabs[2]:
            self.render_compatibility(data)
        with tabs[3]:
            self.render_graph(data)
        with tabs[4]:
            self.render_manage(data)

    # ------------------------------------------------------------------
    def render_sidebar(self):
        st.sidebar.header("Tutor capacity policy")

        mode_label = st.sidebar.radio(
            "Capacity source",
            ["Use each tutor's stored capacity", "Same capacity for all tutors"],
        )

        uniform = 1
        if mode_label.startswith("Same"):
            uniform = st.sidebar.number_input(
                "Students per tutor", min_value=0, max_value=50, value=1, step=1
            )

        st.sidebar.divider()
        st.sidebar.header("Database")
        confirm = st.sidebar.checkbox("I want to reset to the seed data")
        if st.sidebar.button("Reset database", disabled=not confirm):
            reset_database(self.admin_user_id)
            st.cache_data.clear()
            st.rerun()

        return ("uniform" if mode_label.startswith("Same") else "stored"), int(uniform)

    # ------------------------------------------------------------------
    def render_results(self, data):
        n_t, n_s = len(data["tutor_ids"]), len(data["student_ids"])
        matched = len(data["pairs"])
        total_capacity = sum(data["capacities"].values())
        bound = min(n_s, total_capacity)

        cols = st.columns(4)
        cols[0].metric("Tutors |T|", n_t)
        cols[1].metric("Students |S|", n_s)
        cols[2].metric("Compatible pairs |R|", len(data["relation"]))
        cols[3].metric("Possible pairs |T×S|", n_t * n_s)

        cols = st.columns(4)
        cols[0].metric("Total capacity Σc", total_capacity)
        cols[1].metric("Students matched |M|", f"{matched} / {n_s}")
        cols[2].metric("Upper bound", bound)
        cols[3].metric(
            "Capacity used",
            f"{matched / total_capacity:.0%}" if total_capacity else "—",
        )

        st.subheader("Assignments")
        if data["matches"]:
            st.dataframe(
                pd.DataFrame(data["matches"]),
                hide_index=True,
            )
        else:
            st.info("No student could be assigned a tutor.")

        st.subheader("Unmatched students")
        if data["unmatched"]:
            st.dataframe(
                pd.DataFrame(data["unmatched"]),
                hide_index=True,
            )
        else:
            st.success("Every student has a tutor.")

        st.subheader("Constraint checks")
        tutor_load = Counter(t for t, _ in data["pairs"])
        student_load = Counter(s for _, s in data["pairs"])
        edges = set(data["relation"])

        checks = {
            "M ⊆ R (every assignment is a compatible pair)": all(
                p in edges for p in data["pairs"]
            ),
            "deg(s) ≤ 1 for every student": all(
                v <= 1 for v in student_load.values()
            ),
            "deg(t) ≤ c_t for every tutor": all(
                tutor_load[t] <= data["capacities"][t] for t in tutor_load
            ),
            "|M| ≤ min(|S|, Σc)": matched <= bound,
            "Graph partitions are valid": data["verification"]["partitions_valid"],
            "Graph edges equal relation R": data["verification"]["edges_valid"],
        }
        st.dataframe(
            pd.DataFrame(
                {
                    "Check": list(checks),
                    "Result": ["Pass" if v else "FAIL" for v in checks.values()],
                }
            ),
            hide_index=True,
        )

        with st.expander("Modeling assumptions"):
            st.markdown(
                "- Capacity `c_t` is the number of students a tutor can take "
                "overall, not per time slot.\n"
                "- Each student receives one tutor (`deg(s) ≤ 1`), even if "
                "they need several subjects.\n"
                "- An assigned pair shares at least one free time slot. "
                "Sessions are not yet reserved, so two students of one tutor "
                "may be offered the same slot (group session).\n"
                "- Several maximum matchings can exist; the one shown is the "
                "one the flow algorithm returned."
            )

    # ------------------------------------------------------------------
    def render_data(self, data):
        left, right = st.columns(2)
        with left:
            st.subheader("Tutors")
            st.dataframe(data["tutors"], hide_index=True)
        with right:
            st.subheader("Students")
            st.dataframe(data["students"], hide_index=True)

        st.subheader("Schedules")
        kind = st.radio("Show schedule of a", ["Student", "Tutor"], horizontal=True)

        ids = data["student_ids"] if kind == "Student" else data["tutor_ids"]
        if not ids:
            st.info(f"There are no {kind.lower()}s yet.")
            return

        person = st.selectbox(
            kind, ids, format_func=lambda i: f"{kind[0]}{i}", key="sched_person"
        )

        svc = Services()
        try:
            if kind == "Student":
                classes = svc.schedules.get_student_schedule(person)
                free = svc.schedules.get_student_free_slots(person)
                a, b = st.columns(2)
                with a:
                    st.markdown("**Classes (busy)**")
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Day": c["day"],
                                    "Start": fmt_time(c["start_time"]),
                                    "End": fmt_time(c["end_time"]),
                                    "Subject": c["subject_code"],
                                }
                                for c in classes
                            ],
                            columns=["Day", "Start", "End", "Subject"],
                        ),
                        hide_index=True,
                    )
                with b:
                    st.markdown("**Free(s), 07:00–17:00**")
                    st.dataframe(
                        slots_to_df(free), hide_index=True
                    )
            else:
                st.markdown("**Available(t)**")
                st.dataframe(
                    slots_to_df(svc.schedules.get_tutor_available_slots(person)),
                    hide_index=True,
                )
        finally:
            svc.close()

    # ------------------------------------------------------------------
    def render_compatibility(self, data):
        st.markdown(
            "`Compatible(t, s) ≡ SubjectMatch ∧ TimeMatch ∧ LanguageMatch`"
        )

        lookup = {(r["tutor_id"], r["student_id"]): r for r in data["reports"]}
        rows = {}
        for t in data["tutor_ids"]:
            row = {}
            for s in data["student_ids"]:
                r = lookup[(t, s)]
                if r["compatible"]:
                    row[f"S{s}"] = "✓"
                else:
                    failed = [
                        name
                        for name, key in (
                            ("subject", "subject_match"),
                            ("time", "time_match"),
                            ("language", "language_match"),
                        )
                        if not r[key]
                    ]
                    row[f"S{s}"] = "✗ " + ", ".join(failed)
            rows[f"T{t}"] = row

        st.dataframe(pd.DataFrame.from_dict(rows, orient="index"))
        st.caption("A ✗ lists the predicates that evaluated to False.")

        if not (data["tutor_ids"] and data["student_ids"]):
            return

        st.subheader("Explain a pair")
        a, b = st.columns(2)
        t = a.selectbox(
            "Tutor", data["tutor_ids"], format_func=lambda i: f"T{i}", key="pair_t"
        )
        s = b.selectbox(
            "Student", data["student_ids"], format_func=lambda i: f"S{i}", key="pair_s"
        )

        svc = Services()
        try:
            subjects_t = svc.sets.get_tutor_subjects(t)
            needs_s = svc.sets.get_student_needs(s)
            langs_t = svc.sets.get_tutor_languages(t)
            langs_s = svc.sets.get_student_languages(s)
            slots = svc.sets.availability_intersection(
                svc.schedules.get_student_free_slots(s),
                svc.schedules.get_tutor_available_slots(t),
            )
            report = svc.logic.evaluate(t, s)
        finally:
            svc.close()

        def mark(ok):
            return "✓ True" if ok else "✗ False"

        st.markdown(
            f"- **SubjectMatch** {mark(report['subject_match'])}: "
            f"Subjects(t) ∩ Needs(s) = {sorted(subjects_t & needs_s) or '∅'}\n"
            f"- **TimeMatch** {mark(report['time_match'])}: "
            f"Free(s) ∩ Available(t) = "
            f"{[fmt_slot(x) for x in slots] or '∅'}\n"
            f"- **LanguageMatch** {mark(report['language_match'])}: "
            f"Lang(t) ∩ Lang(s) = {sorted(langs_t & langs_s) or '∅'}\n"
            f"- **Compatible(T{t}, S{s})** {mark(report['compatible'])}"
        )

    # ------------------------------------------------------------------
    def render_graph(self, data):
        if not (data["tutor_ids"] and data["student_ids"]):
            st.info("Add at least one tutor and one student to draw the graph.")
            return

        visualizer = TUGMAVisualizer()
        left, right = st.columns(2)

        with left:
            fig = visualizer.draw_before_matching(data["graph"])
            st.pyplot(fig)
            plt.close(fig)
        with right:
            fig = visualizer.draw_after_matching(data["graph"], data["pairs"])
            st.pyplot(fig)
            plt.close(fig)

        st.subheader("Remaining tutor capacity")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Tutor": f"T{t}",
                        "Capacity": data["capacities"][t],
                        "Assigned": data["capacities"][t] - left_over,
                        "Remaining": left_over,
                    }
                    for t, left_over in sorted(data["remaining"].items())
                ]
            ),
            hide_index=True,
        )

    # ------------------------------------------------------------------
    def render_manage(self, data):
        db = Database(DB_PATH)
        try:
            subjects = db.fetch_all(
                "SELECT subject_id, subject_code, subject_name "
                "FROM subjects ORDER BY subject_id"
            )
            subject_label = {
                r["subject_id"]: f"{r['subject_code']} — {r['subject_name']}"
                for r in subjects
            }

            st.caption("Changes are saved to the SQLite database immediately.")
            student_tab, tutor_tab, slot_tab = st.tabs(
                ["Add student", "Add tutor", "Add class or availability"]
            )

            with student_tab:
                with st.form("add_student", clear_on_submit=True):
                    name = st.text_input("Name")
                    c1, c2 = st.columns(2)
                    year = c1.number_input("Year level", 1, 6, 2)
                    course = c2.text_input("Course", "BCS")
                    needs = st.multiselect(
                        "Subjects needed",
                        list(subject_label),
                        format_func=subject_label.get,
                    )
                    langs = st.multiselect("Languages", LANGUAGES, default=LANGUAGES[:1])
                    submitted = st.form_submit_button("Add student")

                if submitted:
                    if not (name.strip() and needs and langs):
                        st.error("Enter a name, at least one subject, and one language.")
                    else:
                        cur = db.execute(
                            "INSERT INTO students (name, grade_level, course) "
                            "VALUES (?, ?, ?)",
                            (name.strip(), int(year), course.strip() or "BCS"),
                        )
                        sid = cur.lastrowid
                        for subj in needs:
                            db.execute(
                                "INSERT INTO student_subjects VALUES (?, ?)",
                                (sid, subj),
                            )
                        for lang in langs:
                            db.execute(
                                "INSERT INTO student_languages VALUES (?, ?)",
                                (sid, lang),
                            )
                        st.cache_data.clear()
                        st.rerun()

            with tutor_tab:
                with st.form("add_tutor", clear_on_submit=True):
                    name = st.text_input("Name", key="tutor_name")
                    c1, c2, c3 = st.columns(3)
                    year = c1.number_input("Year level", 1, 6, 3, key="tutor_year")
                    course = c2.text_input("Course", "BCS", key="tutor_course")
                    capacity = c3.number_input("Capacity", 1, 50, 5)
                    verified = st.checkbox("Verified", value=True)
                    subs = st.multiselect(
                        "Subjects taught",
                        list(subject_label),
                        format_func=subject_label.get,
                        key="tutor_subjects",
                    )
                    langs = st.multiselect(
                        "Languages",
                        LANGUAGES,
                        default=LANGUAGES[:1],
                        key="tutor_langs",
                    )
                    submitted = st.form_submit_button("Add tutor")

                if submitted:
                    if not (name.strip() and subs and langs):
                        st.error("Enter a name, at least one subject, and one language.")
                    else:
                        cur = db.execute(
                            "INSERT INTO tutors "
                            "(name, grade_level, course, verified, capacity) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (
                                name.strip(),
                                int(year),
                                course.strip() or "BCS",
                                int(verified),
                                int(capacity),
                            ),
                        )
                        tid = cur.lastrowid
                        for subj in subs:
                            db.execute(
                                "INSERT INTO tutor_subjects VALUES (?, ?)",
                                (tid, subj),
                            )
                        for lang in langs:
                            db.execute(
                                "INSERT INTO tutor_languages VALUES (?, ?)",
                                (tid, lang),
                            )
                        st.cache_data.clear()
                        st.rerun()

            with slot_tab:
                kind = st.radio(
                    "Add a", ["Student class", "Tutor availability"], horizontal=True
                )
                is_class = kind == "Student class"
                ids = data["student_ids"] if is_class else data["tutor_ids"]

                if not ids:
                    st.info("Add a person first.")
                else:
                    with st.form("add_slot", clear_on_submit=True):
                        person = st.selectbox(
                            "Person", ids, format_func=lambda i: f"{'S' if is_class else 'T'}{i}"
                        )
                        day = st.selectbox("Day", DAYS)
                        c1, c2 = st.columns(2)
                        start = c1.time_input("Start", time(8, 0), step=900)
                        end = c2.time_input("End", time(10, 0), step=900)
                        subj = None
                        if is_class:
                            subj = st.selectbox(
                                "Subject",
                                list(subject_label),
                                format_func=subject_label.get,
                            )
                        submitted = st.form_submit_button("Add")

                    if submitted:
                        if start >= end:
                            st.error("The start time must be before the end time.")
                        else:
                            s_txt, e_txt = start.strftime("%H:%M"), end.strftime("%H:%M")
                            if is_class:
                                db.execute(
                                    "INSERT INTO student_schedule "
                                    "(student_id, day, start_time, end_time, subject_id) "
                                    "VALUES (?, ?, ?, ?, ?)",
                                    (person, day, s_txt, e_txt, subj),
                                )
                            else:
                                db.execute(
                                    "INSERT INTO tutor_availability "
                                    "(tutor_id, day, start_time, end_time) "
                                    "VALUES (?, ?, ?, ?)",
                                    (person, day, s_txt, e_txt),
                                )
                            st.cache_data.clear()
                            st.rerun()
        finally:
            db.close()


def main():
    st.set_page_config(page_title="TUGMA", page_icon="🎓", layout="wide")
    ensure_database()

    session_user = st.session_state.get("user")
    if session_user is None:
        render_auth(DB_PATH)
        return

    # Re-verify the account on every rerun (disabled or deleted accounts
    # lose access immediately).
    db = Database(DB_PATH)
    try:
        user = get_user(db, session_user["user_id"])
    finally:
        db.close()

    if user is None:
        st.session_state.pop("user", None)
        st.rerun()

    st.session_state["user"] = user
    st.sidebar.markdown(f"**{user['name']}**  \n{user['role'].title()}")
    if st.sidebar.button("Log out"):
        st.session_state.pop("user", None)
        st.rerun()
    st.sidebar.divider()

    if user["role"] == "admin":
        TUGMAApp().render(user["user_id"])
    else:
        st.title("TUGMA")
        st.info(
            f"Welcome, {user['name']}. The {user['role']} dashboard is built "
            "in the next phase."
        )


main()
