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


# ----------------------------------------------------------------------
# Application
# ----------------------------------------------------------------------
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
        if cell in ("Free", "Available"):
            return "background-color: #d9f2e3; color: #14532d"
        return "background-color: #fde2e2; color: #7f1d1d"

    styler = df.style
    return (getattr(styler, "map", None) or styler.applymap)(color)


class TUGMAApp:
    """Administrator portal, written for non-technical staff."""

    PAGES = [
        "Home",
        "Matches",
        "People",
        "Can these two be matched?",
        "Accounts",
        "Settings",
        "How the matching works",
    ]

    def render(self, admin_user_id):
        self.admin_user_id = admin_user_id
        st.session_state.setdefault("cap_mode", "stored")
        st.session_state.setdefault("cap_uniform", 1)

        data = run_pipeline(
            DB_PATH.stat().st_mtime_ns,
            st.session_state["cap_mode"],
            int(st.session_state["cap_uniform"]),
        )
        self.data = data
        self.tname = dict(zip(data["tutors"]["tutor_id"], data["tutors"]["name"]))
        self.sname = dict(
            zip(data["students"]["student_id"], data["students"]["name"])
        )

        page = st.sidebar.radio("Go to", self.PAGES, key="admin_page")
        {
            "Home": self.page_home,
            "Matches": self.page_matches,
            "People": self.page_people,
            "Can these two be matched?": self.page_pair,
            "Accounts": self.page_accounts,
            "Settings": self.page_settings,
            "How the matching works": self.page_technical,
        }[page]()

    # -------------------------------------------------------- helpers
    def subj(self, codes):
        names = self.data["subject_names"]
        return [names.get(c, c) for c in codes]

    def subj_text(self, csv_codes):
        if not csv_codes:
            return "—"
        return ", ".join(self.subj([c.strip() for c in csv_codes.split(",")]))

    def why_unmatched(self, student_id, has_compatible):
        if has_compatible:
            return "Every tutor who could help is already full."

        reports = [r for r in self.data["reports"] if r["student_id"] == student_id]
        by_subject = [r for r in reports if r["subject_match"]]
        if not by_subject:
            return "No tutor teaches the subject this student needs."
        by_time = [r for r in by_subject if r["time_match"]]
        if not by_time:
            return "The tutors who teach it are never free when the student is."
        if not [r for r in by_time if r["language_match"]]:
            return "The tutors who are free speak a different language."
        return "No single tutor fits subject, free time and language together."

    # ----------------------------------------------------------- Home
    def page_home(self):
        d = self.data
        n_s, n_t = len(d["student_ids"]), len(d["tutor_ids"])
        matched = len(d["pairs"])

        st.header("Home")
        if not (n_s and n_t):
            st.warning("There are no students or no tutors yet.")
            return

        st.subheader(f"{matched} of {n_s} students have a tutor")
        st.progress(matched / n_s)

        c = st.columns(4)
        c[0].metric("Students", n_s)
        c[1].metric("Tutors", n_t)
        c[2].metric("Students with a tutor", matched)
        c[3].metric("Students still waiting", n_s - matched)

        st.subheader("Needs attention")
        if d["unmatched"]:
            for item in d["unmatched"]:
                name = self.sname[item["student_id"]]
                reason = self.why_unmatched(
                    item["student_id"], item["has_compatible"]
                )
                st.warning(f"**{name}** has no tutor yet. {reason}")
        else:
            st.success("Every student has a tutor.")

        full = [t for t, left in d["remaining"].items() if left == 0]
        if full:
            st.info(
                "Tutors with no spots left: "
                + ", ".join(self.tname[t] for t in full)
            )

    # -------------------------------------------------------- Matches
    def page_matches(self):
        d = self.data
        st.header("Matches")
        st.caption(
            "Each student is given at most one tutor, and no tutor is given "
            "more students than they agreed to take."
        )

        st.subheader("Who is matched with whom")
        if d["matches"]:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Student": self.sname[m["student_id"]],
                            "Tutor": self.tname[m["tutor_id"]],
                            "Subject": ", ".join(self.subj(m["shared"])),
                            "Times they can both meet": "; ".join(
                                fmt_range(x) for x in m["slots"]
                            ),
                        }
                        for m in d["matches"]
                    ]
                ),
                hide_index=True,
            )
            st.caption(
                "These are possible meeting times, not booked sessions."
            )
        else:
            st.info("No student has been matched yet.")

        st.subheader("How busy is each tutor?")
        load = Counter(t for t, _ in d["pairs"])
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Tutor": self.tname[t],
                        "Students": load[t],
                        "Spots left": d["remaining"][t],
                        "Most students they can take": d["capacities"][t],
                    }
                    for t in d["tutor_ids"]
                ]
            ),
            hide_index=True,
        )

        st.subheader("Students without a tutor")
        if d["unmatched"]:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Student": self.sname[u["student_id"]],
                            "Why": self.why_unmatched(
                                u["student_id"], u["has_compatible"]
                            ),
                        }
                        for u in d["unmatched"]
                    ]
                ),
                hide_index=True,
            )
        else:
            st.success("Every student has a tutor.")

    # --------------------------------------------------------- People
    def page_people(self):
        d = self.data
        st.header("People")
        kind = st.radio("Show", ["Students", "Tutors"], horizontal=True)

        if kind == "Students":
            df = d["students"]
            st.dataframe(
                pd.DataFrame(
                    {
                        "Name": df["name"],
                        "Course": df["course"],
                        "Year": df["year"],
                        "Needs help with": df["needs"].map(self.subj_text),
                        "Languages": df["languages"],
                    }
                ),
                hide_index=True,
            )
            ids, names = d["student_ids"], self.sname
        else:
            df = d["tutors"]
            st.dataframe(
                pd.DataFrame(
                    {
                        "Name": df["name"],
                        "Course": df["course"],
                        "Year": df["year"],
                        "Can teach": df["subjects"].map(self.subj_text),
                        "Languages": df["languages"],
                        "Most students": df["capacity"],
                        "Verified": df["verified"].map({True: "Yes", False: "No"}),
                    }
                ),
                hide_index=True,
            )
            ids, names = d["tutor_ids"], self.tname

        if not ids:
            return

        st.subheader("Weekly timetable")
        person = st.selectbox(
            kind[:-1], ids, format_func=lambda i: names[i], key=f"person_{kind}"
        )

        svc = Services()
        try:
            if kind == "Students":
                classes = svc.schedules.get_student_schedule(person)
                blocks = [
                    {
                        "day": c["day"],
                        "start_time": c["start_time"],
                        "end_time": c["end_time"],
                        "text": c["subject_code"],
                    }
                    for c in classes
                ]
                free = svc.schedules.get_student_free_slots(person)
                st.caption("Red = in class. Green = free for tutoring.")
                shown = blocks + [{**f, "text": "Free"} for f in free]
            else:
                avail = svc.schedules.get_tutor_available_slots(person)
                st.caption("Green = available to tutor.")
                shown = [{**a, "text": "Available"} for a in avail]
        finally:
            svc.close()

        st.dataframe(timetable(shown, "Free"))

    # ----------------------------------------------------------- Pair
    def page_pair(self):
        d = self.data
        st.header("Can these two be matched?")
        st.caption(
            "A tutor and a student can be matched only if the tutor teaches "
            "a subject the student needs, they are both free at some "
            "time, and they speak a common language."
        )

        if not (d["tutor_ids"] and d["student_ids"]):
            st.info("Add at least one tutor and one student first.")
            return

        lookup = {(r["tutor_id"], r["student_id"]): r for r in d["reports"]}

        a, b = st.columns(2)
        t = a.selectbox(
            "Tutor", d["tutor_ids"], format_func=lambda i: self.tname[i], key="pair_t"
        )
        s = b.selectbox(
            "Student",
            d["student_ids"],
            format_func=lambda i: self.sname[i],
            key="pair_s",
        )

        svc = Services()
        try:
            teach = svc.sets.get_tutor_subjects(t)
            need = svc.sets.get_student_needs(s)
            langs = svc.sets.get_tutor_languages(t) & svc.sets.get_student_languages(s)
            slots = svc.sets.availability_intersection(
                svc.schedules.get_student_free_slots(s),
                svc.schedules.get_tutor_available_slots(t),
            )
        finally:
            svc.close()

        r = lookup[(t, s)]
        shared = sorted(teach & need)

        def line(ok, yes, no):
            (st.success if ok else st.error)(yes if ok else no)

        line(
            r["subject_match"],
            "Subject: " + self.tname[t] + " teaches " + ", ".join(self.subj(shared)) + ".",
            f"Subject: {self.tname[t]} does not teach anything {self.sname[s]} needs.",
        )
        line(
            r["time_match"],
            "Time: they can both meet on "
            + "; ".join(fmt_range(x) for x in slots[:4])
            + (" and more." if len(slots) > 4 else "."),
            "Time: they are never free at the same time.",
        )
        line(
            r["language_match"],
            "Language: they both speak " + " and ".join(sorted(langs)) + ".",
            "Language: they have no language in common.",
        )

        if r["compatible"]:
            st.success(f"**{self.tname[t]} and {self.sname[s]} can be matched.**")
        else:
            st.error(f"**{self.tname[t]} and {self.sname[s]} cannot be matched.**")

        st.subheader("Everyone at a glance")
        rows = {}
        for tid in d["tutor_ids"]:
            row = {}
            for sid in d["student_ids"]:
                rep = lookup[(tid, sid)]
                if rep["compatible"]:
                    row[self.sname[sid]] = "Yes"
                else:
                    why = [
                        n
                        for n, k in (
                            ("subject", "subject_match"),
                            ("time", "time_match"),
                            ("language", "language_match"),
                        )
                        if not rep[k]
                    ]
                    row[self.sname[sid]] = "No: " + ", ".join(why)
            rows[self.tname[tid]] = row
        st.dataframe(pd.DataFrame.from_dict(rows, orient="index"))
        st.caption("Rows are tutors, columns are students.")

    # -------------------------------------------------------- Accounts
    def page_accounts(self):
        st.header("Accounts")
        st.caption(
            "People who registered and can log in. Students and tutors from "
            "the demo data do not have accounts."
        )

        db = Database(DB_PATH)
        try:
            accounts = list_accounts(db, self.admin_user_id)
        finally:
            db.close()

        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Name": a["name"],
                        "Email": a["email"],
                        "Type": a["role"].title(),
                        "Status": "Active" if a["is_active"] else "Disabled",
                    }
                    for a in accounts
                ]
            ),
            hide_index=True,
        )

        others = [a for a in accounts if a["user_id"] != self.admin_user_id]
        if not others:
            return

        st.subheader("Turn an account on or off")
        picked = st.selectbox(
            "Account",
            others,
            format_func=lambda a: f"{a['name']} ({a['email']})",
        )
        enable = not picked["is_active"]
        if st.button("Enable account" if enable else "Disable account"):
            db = Database(DB_PATH)
            try:
                set_account_active(db, self.admin_user_id, picked["user_id"], enable)
            except (AuthError, PermissionDenied) as error:
                st.error(str(error))
            else:
                st.rerun()
            finally:
                db.close()

    # -------------------------------------------------------- Settings
    def page_settings(self):
        st.header("Settings")

        st.subheader("How many students can a tutor take?")
        choice = st.radio(
            "Rule",
            ["Each tutor's own limit", "The same limit for every tutor"],
            index=0 if st.session_state["cap_mode"] == "stored" else 1,
            key="cap_choice",
        )
        st.session_state["cap_mode"] = (
            "stored" if choice.startswith("Each") else "uniform"
        )
        if st.session_state["cap_mode"] == "uniform":
            st.number_input(
                "Students per tutor", 0, 50, step=1, key="cap_uniform"
            )

        st.divider()
        st.subheader("Reset the demo data")
        st.warning(
            "This replaces all students, tutors and schedules with the "
            "original demo data. Administrator accounts are kept."
        )
        sure = st.checkbox("Yes, I want to erase the current data")
        if st.button("Reset demo data", disabled=not sure):
            try:
                reset_database(self.admin_user_id)
            except PermissionDenied as error:
                st.error(str(error))
            else:
                st.cache_data.clear()
                st.rerun()

    # ------------------------------------------------------ Technical
    def page_technical(self):
        d = self.data
        st.header("How the matching works")
        st.caption(
            "For presentations and grading. Everything here is produced by "
            "the same calculation that created the matches."
        )

        st.markdown(
            "1. **Check every tutor–student pair.** A pair is *compatible* "
            "when `SubjectMatch ∧ TimeMatch ∧ LanguageMatch` are all true.\n"
            "2. **Draw a graph.** Tutors on the left, students on the "
            "right, a line wherever a pair is compatible.\n"
            "3. **Pick the best set of lines.** Give as many students as "
            "possible a tutor, never more than one tutor per student and "
            "never more students than a tutor's limit."
        )

        n_t, n_s = len(d["tutor_ids"]), len(d["student_ids"])
        c = st.columns(3)
        c[0].metric("Pairs checked (|T×S|)", n_t * n_s)
        c[1].metric("Compatible pairs (|R|)", len(d["relation"]))
        c[2].metric("Students matched (|M|)", len(d["pairs"]))

        st.subheader("Safety checks")
        tutor_load = Counter(t for t, _ in d["pairs"])
        student_load = Counter(s for _, s in d["pairs"])
        edges = set(d["relation"])
        bound = min(n_s, sum(d["capacities"].values()))
        checks = {
            "Every match is a compatible pair (M ⊆ R)": all(
                p in edges for p in d["pairs"]
            ),
            "No student has more than one tutor (deg(s) ≤ 1)": all(
                v <= 1 for v in student_load.values()
            ),
            "No tutor is over their limit (deg(t) ≤ c)": all(
                tutor_load[t] <= d["capacities"][t] for t in tutor_load
            ),
            "Matches never exceed what is possible (|M| ≤ min(|S|, Σc))": len(
                d["pairs"]
            )
            <= bound,
            "The graph has two separate sides": d["verification"]["partitions_valid"],
            "The graph's lines equal the compatible pairs": d["verification"][
                "edges_valid"
            ],
        }
        for text, ok in checks.items():
            (st.success if ok else st.error)(("Passed: " if ok else "FAILED: ") + text)

        if n_t and n_s:
            st.subheader("The graph, before and after")
            visualizer = TUGMAVisualizer()
            left, right = st.columns(2)
            with left:
                fig = visualizer.draw_before_matching(d["graph"])
                st.pyplot(fig)
                plt.close(fig)
                st.caption("Every compatible pair.")
            with right:
                fig = visualizer.draw_after_matching(d["graph"], d["pairs"])
                st.pyplot(fig)
                plt.close(fig)
                st.caption("The pairs chosen.")

        with st.expander("Assumptions of this model"):
            st.markdown(
                "- A tutor's limit is the number of students over the "
                "whole week, not per time slot.\n"
                "- Each student gets one tutor, even if they need help in "
                "several subjects.\n"
                "- Meeting times are possible times only. Nothing is booked, "
                "so two students of one tutor can be offered the same time.\n"
                "- Several equally good matchings can exist; the one shown "
                "is the one the calculation returned."
            )


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