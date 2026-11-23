# Student / Tutor portal: one shell, with a Learning / Tutoring mode toggle.
# Accounts with both profiles can switch modes; others see only their own.

from contextlib import contextmanager
from datetime import datetime

import pandas as pd
import streamlit as st

import services.account_service as acct
import services.session_service as sess
from services.auth_service import AuthError, PermissionDenied
from services.migrations import DB_PATH
from views.components import STATUS_CHIPS, person_header
from services.pipeline import DAYS, Services, fmt12, run_pipeline, timetable
from src.database import Database
from src.relations import CompatibilityRelation
from views.profile import render_profile

PAGES = ["Home", "Classes", "Calendar", "Sessions", "People", "Profile"]


# ------------------------------------------------------------- helpers
@contextmanager
def db_conn():
    db = Database(DB_PATH)
    try:
        yield db
    finally:
        db.close()


def act(function, *args):
    """Run a service call; show its error, or rerun the page on success."""
    error = None
    with db_conn() as db:
        try:
            function(db, *args)
        except (AuthError, PermissionDenied) as exc:
            error = str(exc)
    if error:
        st.error(error)
        return False
    st.rerun()


@st.cache_resource
def _snapshots():
    return {}


def get_snapshot(force=False):
    """The matching run everyone sees. It only changes when someone presses
    Refresh, so a student's suggestion does not shift on every edit."""
    store = _snapshots()
    if force or "data" not in store:
        mtime = DB_PATH.stat().st_mtime_ns
        store["data"] = run_pipeline(mtime, "stored", 1)
        store["mtime"] = mtime
        store["at"] = datetime.now()
    return store


def subject_options(db):
    return {
        r["subject_id"]: f"{r['subject_code']} · {r['subject_name'].title()}"
        for r in db.fetch_all("SELECT * FROM subjects ORDER BY subject_code")
    }


def when(row):
    day = datetime.strptime(row["session_date"], "%Y-%m-%d")
    return f"{day:%a, %b} {day.day} · {fmt12(row['start_time'])} – {fmt12(row['end_time'])}"


# ---------------------------------------------------------------- shell
def render_portal(user):
    modes = user["modes"]
    if not modes:
        st.error("This account has no student or tutor profile.")
        return

    page = st.sidebar.radio("Go to", PAGES, key="portal_page")
    if page == "Profile":
        mode = (
            modes[0]
            if len(modes) == 1
            else st.radio("Mode", modes, key="mode", horizontal=True)
        )
        render_profile(user, mode)
        return
    mode = (
        modes[0]
        if len(modes) == 1
        else st.sidebar.radio("Mode", modes, key="mode", horizontal=True)
    )

    st.header(page)
    st.caption(
        "Learning: find tutors for your classes."
        if mode == "Learning"
        else "Tutoring: help classmates with the subjects you teach."
    )

    {
        "Home": page_home,
        "Classes": page_classes,
        "Calendar": page_calendar,
        "Sessions": page_sessions,
        "People": page_people,
    }[page](user, mode)


# ----------------------------------------------------------------- Home
def page_home(user, mode):
    uid = user["user_id"]
    with db_conn() as db:
        tabs = sess.list_sessions(db, uid, mode)
        if mode == "Learning":
            n_needs = db.fetch_one(
                "SELECT COUNT(*) n FROM student_subjects WHERE student_id=?",
                (user["student_id"],))["n"]
        else:
            n_teach = db.fetch_one(
                "SELECT COUNT(*) n FROM tutor_subjects WHERE tutor_id=?",
                (user["tutor_id"],))["n"]
            tutor = db.fetch_one("SELECT verified, capacity FROM tutors WHERE tutor_id=?",
                                 (user["tutor_id"],))
            taken = db.fetch_one(
                "SELECT COUNT(DISTINCT student_id) n FROM sessions "
                "WHERE tutor_id=? AND status='confirmed'", (user["tutor_id"],))["n"]
        langs = _languages(db, user, mode)

    st.subheader(f"Hello, {user['name'].split()[0]}")
    c = st.columns(4)
    if mode == "Learning":
        c[0].metric("Classes I need help with", n_needs)
        c[1].metric("Upcoming sessions", len(tabs["upcoming"]))
        c[2].metric("Requests waiting", len(tabs["sent"]))
        _suggestion(user)
    else:
        c[0].metric("Subjects I teach", n_teach)
        c[1].metric("Requests to answer", len(tabs["reply"]))
        c[2].metric("Upcoming sessions", len(tabs["upcoming"]))
        c[3].metric("Students / capacity", f"{taken} / {tutor['capacity']}")
        if not tutor["verified"]:
            st.warning(
                "Your tutor profile is not verified yet. Students will not "
                "see you until an administrator verifies it."
            )

    st.subheader("Upcoming sessions")
    if tabs["upcoming"]:
        for row in tabs["upcoming"][:3]:
            session_card(row, mode, uid, "home")
    else:
        st.info("No upcoming sessions.")

    with st.expander("My profile"):
        kind = "student" if mode == "Learning" else "tutor"
        picked = st.multiselect("Languages", acct.LANGUAGES, default=langs,
                                key=f"langs_{mode}")
        if st.button("Save languages", key=f"save_langs_{mode}"):
            act(acct.set_languages, uid, kind, picked)
        if mode == "Tutoring":
            cap = st.number_input("Most students I can take", 1, 50,
                                  int(tutor["capacity"]), key="cap_input")
            if st.button("Save capacity"):
                act(acct.set_capacity, uid, int(cap))
        other = "tutor" if mode == "Learning" else "student"
        if user[f"{other}_id"] is None and st.button(
            f"Also become a {other}", key="add_profile"
        ):
            act(acct.add_profile, uid, other)


def _languages(db, user, mode):
    table, col, pid = (
        ("student_languages", "student_id", user["student_id"])
        if mode == "Learning"
        else ("tutor_languages", "tutor_id", user["tutor_id"])
    )
    return [r["language"] for r in
            db.fetch_all(f"SELECT language FROM {table} WHERE {col}=?", (pid,))]


def _suggestion(user):
    snap = get_snapshot()
    data = snap["data"]
    st.subheader("Suggested tutor")
    stale = snap["mtime"] != DB_PATH.stat().st_mtime_ns
    st.caption(
        f"From the matching run at {snap['at']:%I:%M %p}. "
        + ("Your data changed since then. Press refresh to include it." if stale else "")
    )
    if st.button("Refresh suggestions", key="refresh"):
        get_snapshot(force=True)
        st.rerun()

    me = user["student_id"]
    names = dict(zip(data["tutors"]["tutor_id"], data["tutors"]["name"]))
    match = next((m for m in data["matches"] if m["student_id"] == me), None)
    if match:
        subjects = ", ".join(data["subject_names"].get(c, c) for c in match["shared"])
        with st.container(border=True):
            person_header(names[match["tutor_id"]], f"Can help with {subjects}",
                          "Suggested")
            st.caption("Possible times: " + "; ".join(
                f"{x['day'][:3]} {fmt12(x['start_time'])}–{fmt12(x['end_time'])}"
                for x in match["slots"]))
            st.caption("Request a session from the Classes page.")
    elif me in data["student_ids"]:
        st.info("The matching found no tutor for you yet.")
    else:
        st.info("You are not in this matching run yet. Press refresh.")


# -------------------------------------------------------------- Classes
def page_classes(user, mode):
    uid = user["user_id"]
    with db_conn() as db:
        options = subject_options(db)
        if mode == "Learning":
            held = db.fetch_all(
                "SELECT ss.subject_id, ss.note FROM student_subjects ss "
                "WHERE ss.student_id = ?", (user["student_id"],))
        else:
            held = db.fetch_all("SELECT subject_id, NULL AS note FROM tutor_subjects "
                                "WHERE tutor_id = ?", (user["tutor_id"],))
    owned = {r["subject_id"]: r["note"] for r in held}

    left, right = st.columns([1, 2])
    with left:
        st.subheader("Classes I need help with" if mode == "Learning"
                     else "Subjects I can teach")
        with st.form(f"add_subject_{mode}", clear_on_submit=True):
            choice = st.selectbox(
                "Subject", [s for s in options if s not in owned],
                format_func=options.get)
            note = st.text_input("What are you stuck on?") if mode == "Learning" else ""
            submitted = st.form_submit_button("Add")
        if submitted and choice is not None:
            act(acct.add_need if mode == "Learning" else acct.add_teach, uid,
                *((choice, note) if mode == "Learning" else (choice,)))

        for sid in owned:
            a, b = st.columns([5, 1])
            a.write(options[sid] + (f"  \n_{owned[sid]}_" if owned[sid] else ""))
            if b.button("✕", key=f"rm_{mode}_{sid}"):
                act(acct.remove_need if mode == "Learning" else acct.remove_teach,
                    uid, sid)

    with right:
        if not owned:
            st.info("Add a subject to see " + ("tutors." if mode == "Learning" else "students."))
            return
        picked = st.radio("Show for", list(owned), format_func=options.get,
                          horizontal=True, key=f"focus_{mode}")
        if mode == "Learning":
            _tutors_for(user, picked, options)
        else:
            _students_for(user, picked, options)


def _tutors_for(user, subject_id, options):
    code = options[subject_id].split(" · ")[0]
    me = user["student_id"]
    snap = get_snapshot()["data"]
    suggested = next((m["tutor_id"] for m in snap["matches"] if m["student_id"] == me), None)

    svc = Services()
    try:
        found = []
        for t in CompatibilityRelation(svc.logic).get_tutors():
            report = svc.logic.evaluate(t, me)
            if report["compatible"] and code in svc.sets.get_tutor_subjects(t):
                row = svc.db.fetch_one(
                    "SELECT name, course, grade_level, capacity FROM tutors WHERE tutor_id=?", (t,))
                load = svc.db.fetch_one(
                    "SELECT COUNT(DISTINCT student_id) n FROM sessions "
                    "WHERE tutor_id=? AND status='confirmed'", (t,))["n"]
                found.append((t, row, load, sess.common_slots(svc.db, t, me),
                              svc.sets.language_intersection(
                                  svc.sets.get_tutor_languages(t),
                                  svc.sets.get_student_languages(me))))
    finally:
        svc.close()

    st.subheader(f"Tutors available ({len(found)})")
    if not found:
        st.info("No tutor fits this class yet. A tutor must teach it, speak "
                "your language, and be free when you are.")
    for t, row, load, slots, langs in found:
        with st.container(border=True):
            person_header(row["name"], f"{row['course']} · year {row['grade_level']}",
                          "Suggested by matching" if t == suggested else None)
            st.markdown("**Why you matched**")
            st.write(f"✓ Teaches {options[subject_id].split(' · ')[1]}")
            st.write("✓ Free when you are: " + ", ".join(
                f"{s['day'][:3]} {fmt12(s['start_time'])}–{fmt12(s['end_time'])}"
                for s in slots[:4]) + (" …" if len(slots) > 4 else ""))
            st.write("✓ Speaks " + " and ".join(sorted(langs)))
            if load >= row["capacity"]:
                st.warning("This tutor has no spots left.")
                continue
            with st.expander("Request tutoring"):
                _request_form(user, t, subject_id, slots)


def _request_form(user, tutor_id, subject_id, slots):
    windows = [(d, s["start_time"], s["end_time"]) for s in slots
               for d in sess.upcoming_dates(s["day"], 3)]
    windows.sort()
    labels = {w: f"{w[0]:%a %b} {w[0].day} · free {fmt12(w[1])}–{fmt12(w[2])}"
              for w in windows}
    with st.form(f"req_{tutor_id}_{subject_id}"):
        chosen = st.selectbox("Day", windows, format_func=labels.get)
        start = st.time_input("Start", datetime.strptime(chosen[1], "%H:%M").time(),
                              step=900)
        minutes = st.selectbox("Length", [30, 60, 90, 120], index=1,
                               format_func=lambda m: f"{m} minutes")
        note = st.text_input("Message (optional)")
        go = st.form_submit_button("Send request")
    if go:
        begin = datetime.combine(chosen[0], start)
        end = begin + pd.Timedelta(minutes=minutes)
        if end.date() != chosen[0]:
            st.error("The session must end the same day.")
            return
        act(sess.request_session, user["user_id"], tutor_id, subject_id,
            chosen[0].isoformat(), begin.strftime("%H:%M"), end.strftime("%H:%M"), note)


def _students_for(user, subject_id, options):
    code = options[subject_id].split(" · ")[0]
    st.subheader("Students who need this")
    with db_conn() as db:
        verified = db.fetch_one("SELECT verified FROM tutors WHERE tutor_id=?",
                                (user["tutor_id"],))["verified"]
    if not verified:
        st.info("You will see students once an administrator verifies you.")
        return

    svc = Services()
    try:
        rows = []
        for s in [r["student_id"] for r in svc.db.fetch_all("SELECT student_id FROM students")]:
            if svc.logic.evaluate(user["tutor_id"], s)["compatible"] and code in svc.sets.get_student_needs(s):
                info = svc.db.fetch_one(
                    "SELECT s.name, s.course, ss.note FROM students s "
                    "JOIN student_subjects ss ON ss.student_id = s.student_id "
                    "WHERE s.student_id = ? AND ss.subject_id = ?", (s, subject_id))
                rows.append({"Student": info["name"], "Course": info["course"],
                             "Stuck on": info["note"] or "—"})
    finally:
        svc.close()
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True)
        st.caption("Students request you from their own Classes page.")
    else:
        st.info("No student fits this subject right now.")


# ------------------------------------------------------------- Calendar
def page_calendar(user, mode):
    uid = user["user_id"]
    svc = Services()
    try:
        blocks = []
        if user["student_id"] is not None:
            for c in svc.schedules.get_student_schedule(user["student_id"]):
                blocks.append({"day": c["day"], "start_time": c["start_time"],
                               "end_time": c["end_time"], "text": c["subject_code"]})
            if mode == "Learning":
                blocks += [{**f, "text": "Free"}
                           for f in svc.schedules.get_student_free_slots(user["student_id"])]
        if mode == "Tutoring":
            blocks += [{**a, "text": "Available"}
                       for a in svc.schedules.get_tutor_available_slots(user["tutor_id"])]
        sessions = sess.list_sessions(svc.db, uid, mode)
        classes = svc.db.fetch_all(
            "SELECT ss.schedule_id, ss.day, ss.start_time, ss.end_time, s.subject_code "
            "FROM student_schedule ss JOIN subjects s ON s.subject_id = ss.subject_id "
            "WHERE ss.student_id = ? ORDER BY ss.day, ss.start_time",
            (user["student_id"],)) if user["student_id"] is not None else []
        slots = svc.db.fetch_all(
            "SELECT availability_id, day, start_time, end_time FROM tutor_availability "
            "WHERE tutor_id = ? ORDER BY day, start_time",
            (user["tutor_id"],)) if mode == "Tutoring" else []
        options = subject_options(svc.db)
    finally:
        svc.close()

    this_week = datetime.now().date().isocalendar()[:2]
    for row in sessions["upcoming"] + sessions["sent"] + sessions["reply"]:
        d = datetime.strptime(row["session_date"], "%Y-%m-%d")
        if d.date().isocalendar()[:2] == this_week and d.weekday() < 6:
            blocks.append({"day": DAYS[d.weekday()], "start_time": row["start_time"],
                           "end_time": row["end_time"], "text": "Session"})

    st.caption("Red: classes. Green: " + ("free time." if mode == "Learning"
               else "when you can tutor.") + " Blue: sessions this week.")
    st.dataframe(timetable(blocks, "Free"))

    if user["student_id"] is not None and mode == "Learning":
        st.subheader("My classes")
        with st.form("add_class", clear_on_submit=True):
            c = st.columns(4)
            subject = c[0].selectbox("Subject", list(options), format_func=options.get)
            day = c[1].selectbox("Day", DAYS)
            start = c[2].time_input("Start", datetime.strptime("08:00", "%H:%M").time(), step=900)
            end = c[3].time_input("End", datetime.strptime("09:30", "%H:%M").time(), step=900)
            go = st.form_submit_button("Add class")
        if go:
            act(acct.add_class, uid, subject, day, start.strftime("%H:%M"),
                end.strftime("%H:%M"))
        for r in classes:
            a, b = st.columns([6, 1])
            a.write(f"{r['subject_code']} · {r['day']} {fmt12(r['start_time'])}–{fmt12(r['end_time'])}")
            if b.button("Delete", key=f"dc_{r['schedule_id']}"):
                act(acct.delete_class, uid, r["schedule_id"])

    if mode == "Tutoring":
        st.subheader("When I can tutor")
        with st.form("add_avail", clear_on_submit=True):
            c = st.columns(3)
            day = c[0].selectbox("Day", DAYS)
            start = c[1].time_input("From", datetime.strptime("13:00", "%H:%M").time(), step=900)
            end = c[2].time_input("To", datetime.strptime("15:00", "%H:%M").time(), step=900)
            go = st.form_submit_button("Add availability")
        if go:
            act(acct.add_availability, uid, day, start.strftime("%H:%M"),
                end.strftime("%H:%M"))
        for r in slots:
            a, b = st.columns([6, 1])
            a.write(f"{r['day']} {fmt12(r['start_time'])}–{fmt12(r['end_time'])}")
            if b.button("Delete", key=f"da_{r['availability_id']}"):
                act(acct.delete_availability, uid, r["availability_id"])


# ------------------------------------------------------------- Sessions
def session_card(row, mode, uid, where):
    with st.container(border=True):
        other = row["student_name"] if mode == "Tutoring" else row["tutor_name"]
        label, kind = STATUS_CHIPS[row["status"]]
        person_header(other, row["subject_name"].title(), label, kind)
        st.write(when(row))
        if row["note"]:
            st.caption(row["note"])
        key = f"{where}_{row['session_id']}"
        live = row["status"] in sess.ACTIVE and where != "past"
        if row["status"] == "pending" and mode == "Tutoring" and live:
            a, b = st.columns(2)
            if a.button("Accept", key=f"ok_{key}"):
                act(sess.respond, uid, row["session_id"], True)
            if b.button("Decline", key=f"no_{key}"):
                act(sess.respond, uid, row["session_id"], False)
        elif live:
            if st.button("Cancel session" if row["status"] == "confirmed"
                         else "Cancel request", key=f"cx_{key}"):
                act(sess.cancel, uid, row["session_id"])


def page_sessions(user, mode):
    with db_conn() as db:
        tabs = sess.list_sessions(db, user["user_id"], mode)
    names = (
        [("reply", "Needs your reply"), ("upcoming", "Upcoming"), ("past", "Past")]
        if mode == "Tutoring"
        else [("sent", "Sent"), ("upcoming", "Upcoming"), ("past", "Past")]
    )
    for tab, (key, label) in zip(st.tabs([f"{l} ({len(tabs[k])})" for k, l in names]), names):
        with tab:
            if not tabs[key]:
                st.info("Nothing here yet.")
            for row in tabs[key]:
                session_card(row, mode, user["user_id"], key)


# --------------------------------------------------------------- People
def page_people(user, mode):
    with db_conn() as db:
        if mode == "Learning":
            term = st.text_input("Search tutors by name or subject")
            rows = db.fetch_all(
                "SELECT t.tutor_id, t.name, t.course, t.grade_level FROM tutors t "
                "WHERE t.verified = 1 AND t.tutor_id IS NOT ? ORDER BY t.name",
                (user["tutor_id"],))
            out = []
            for r in rows:
                subs = [x["subject_name"].title() for x in db.fetch_all(
                    "SELECT s.subject_name FROM tutor_subjects ts JOIN subjects s "
                    "ON s.subject_id = ts.subject_id WHERE ts.tutor_id = ?", (r["tutor_id"],))]
                langs = [x["language"] for x in db.fetch_all(
                    "SELECT language FROM tutor_languages WHERE tutor_id = ?", (r["tutor_id"],))]
                out.append({"Name": r["name"], "Course": r["course"],
                            "Year": r["grade_level"], "Teaches": ", ".join(subs) or "—",
                            "Languages": ", ".join(langs) or "—"})
            frame = pd.DataFrame(out)
            if term and not frame.empty:
                frame = frame[frame.apply(lambda r: term.lower() in " ".join(map(str, r)).lower(), axis=1)]
            st.dataframe(frame, hide_index=True)
        else:
            st.subheader("My students")
            rows = db.fetch_all(
                "SELECT DISTINCT s.name, s.course, s.grade_level FROM sessions x "
                "JOIN students s ON s.student_id = x.student_id "
                "WHERE x.tutor_id = ? AND x.status = 'confirmed'", (user["tutor_id"],))
            if rows:
                st.dataframe(pd.DataFrame(
                    [{"Name": r["name"], "Course": r["course"], "Year": r["grade_level"]}
                     for r in rows]), hide_index=True)
            else:
                st.info("Students appear here once you accept a request.")
