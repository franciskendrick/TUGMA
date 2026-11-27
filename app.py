"""Main Flask entry point for the TUGMA web application.

Replaces the legacy Streamlit UI with HTML/CSS/Jinja2 templates connected
directly to src/ (Discrete Structures engine) and services/ (business logic).
"""

import io
import os
from collections import Counter
from datetime import datetime, timedelta
from functools import wraps

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from flask import (
    Flask,
    Response,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from services.account_service import (
    DAYS,
    LANGUAGES,
    add_availability,
    add_class,
    add_need,
    add_profile,
    add_teach,
    delete_availability,
    delete_class,
    remove_need,
    remove_teach,
    set_capacity,
    set_languages,
    set_tutor_verified,
)
from services.auth_service import (
    AuthError,
    PermissionDenied,
    get_user,
    list_accounts,
    login as auth_login,
    register as auth_register,
    require_role,
    set_account_active,
)
from services.migrations import DB_PATH, ensure_database
from services.pipeline import (
    Services,
    fmt12,
    fmt_range,
    run_pipeline,
    to_minutes,
)
from services.profile_service import (
    get_student_profile_data,
    get_tutor_profile_data,
)
from services.session_service import (
    cancel as cancel_session,
    common_slots,
    list_sessions,
    request_session,
    respond as respond_session,
    upcoming_dates,
)
from src.database import Database
from src.visualization import TUGMAVisualizer

app = Flask(__name__)
app.secret_key = os.environ.get("TUGMA_SECRET_KEY", "tugma-dev-secret-key-2026")
app.jinja_env.filters["fmt_range"] = fmt_range
app.jinja_env.filters["fmt12"] = fmt12


# ---------------------------------------------------------------------------
# Helpers & Request Lifecycle
# ---------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = Database(DB_PATH)
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    if "current_user" not in g:
        g.current_user = get_user(get_db(), uid)
    return g.current_user


def initials(name):
    parts = [p for p in (name or "").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def active_mode(user):
    if not user or user["role"] == "admin":
        return None
    modes = user["modes"]
    mode = session.get("mode")
    if mode not in modes and modes:
        mode = modes[0]
        session["mode"] = mode
    return mode


def get_multi_subject_mode():
    db = get_db()
    db.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    row = db.fetch_one("SELECT value FROM app_settings WHERE key = 'multi_subject'")
    if row is None:
        return True
    return bool(row["value"] == "1")


def set_multi_subject_mode(enabled):
    db = get_db()
    db.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    db.execute(
        "INSERT INTO app_settings (key, value) VALUES ('multi_subject', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        ("1" if enabled else "0",),
    )


def get_pipeline_data():
    cap_mode = session.get("cap_mode", "stored")
    cap_uniform = int(session.get("cap_uniform", 1))
    multi_subject = get_multi_subject_mode()
    mtime = DB_PATH.stat().st_mtime_ns if DB_PATH.exists() else 0
    return run_pipeline(mtime, cap_mode, cap_uniform, multi_subject=multi_subject)


@app.context_processor
def inject_globals():
    user = current_user()
    mode = active_mode(user)
    notif_count = 0
    tutor_verified = None
    if user and user["role"] == "member":
        if user["tutor_id"]:
            t_row = get_db().fetch_one("SELECT verified FROM tutors WHERE tutor_id = ?", (user["tutor_id"],))
            tutor_verified = bool(t_row["verified"]) if t_row else False
        if mode:
            try:
                tabs = list_sessions(get_db(), user["user_id"], mode)
                notif_count = len(tabs["reply"]) if mode == "Tutoring" else len(tabs["sent"])
            except Exception:
                notif_count = 0
    return {
        "user": user,
        "mode": mode,
        "tutor_verified": tutor_verified,
        "initials": initials,
        "fmt12": fmt12,
        "fmt_range": fmt_range,
        "notif_count": notif_count,
        "DAYS": DAYS,
        "LANGUAGES": LANGUAGES,
    }


def login_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                session.clear()
                return redirect(url_for("login_page"))
            if role == "admin" and user["role"] != "admin":
                flash("Administrator access is required.", "error")
                return redirect(url_for("home"))
            if role == "member" and user["role"] == "admin":
                return redirect(url_for("admin_home"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator


@app.route("/assets/<path:filename>")
def serve_assets(filename):
    return send_from_directory("assets", filename)


# ---------------------------------------------------------------------------
# Public & Authentication Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    user = current_user()
    if user:
        if user["role"] == "admin":
            return redirect(url_for("admin_home"))
        return redirect(url_for("home"))
    return render_template("landing.html")


@app.route("/login", methods=["GET", "POST"])
def login_page():
    user = current_user()
    if user:
        return redirect(url_for("admin_home" if user["role"] == "admin" else "home"))

    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        try:
            logged_in = auth_login(get_db(), email, password)
            if logged_in["role"] == "admin":
                flash("Administrator accounts must sign in through Admin Login.", "error")
                return render_template("login.html")
            session["user_id"] = logged_in["user_id"]
            session["mode"] = logged_in["modes"][0] if logged_in["modes"] else None
            return redirect(url_for("home"))
        except AuthError as err:
            flash(str(err), "error")
    return render_template("login.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login_page():
    user = current_user()
    if user and user["role"] == "admin":
        return redirect(url_for("admin_home"))

    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        try:
            logged_in = auth_login(get_db(), email, password)
            if logged_in["role"] != "admin":
                flash("This login is restricted to TUGMA administrators.", "error")
            else:
                session["user_id"] = logged_in["user_id"]
                return redirect(url_for("admin_home"))
        except AuthError as err:
            flash(str(err), "error")
    return render_template("admin_login.html")


@app.route("/register", methods=["GET", "POST"])
def register_page():
    if current_user():
        return redirect(url_for("home"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "")
        email = request.form.get("email", "")
        course = request.form.get("course", "")
        role = request.form.get("role", "student")
        try:
            grade_level = int(request.form.get("grade_level", 1))
        except ValueError:
            grade_level = 0
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        try:
            created = auth_register(
                get_db(), full_name, email, password, confirm,
                role, grade_level, course
            )
            session["user_id"] = created["user_id"]
            session["mode"] = created["modes"][0] if created["modes"] else None
            flash("Welcome to TUGMA! Your account has been created.", "success")
            return redirect(url_for("home"))
        except AuthError as err:
            flash(str(err), "error")
    return render_template("register.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/mode", methods=["POST"])
@login_required("member")
def switch_mode():
    user = current_user()
    target = request.form.get("mode")
    if target in user["modes"]:
        session["mode"] = target
    elif target in ("Learning", "Tutoring"):
        kind = "student" if target == "Learning" else "tutor"
        try:
            add_profile(get_db(), user["user_id"], kind)
            session["mode"] = target
            flash(
                "Tutor profile created! An administrator will verify it shortly."
                if kind == "tutor" else "Student profile created!",
                "success",
            )
        except AuthError as err:
            flash(str(err), "error")
    return redirect(request.referrer or url_for("home"))


# ---------------------------------------------------------------------------
# Member Portal: Home
# ---------------------------------------------------------------------------
@app.route("/home")
@login_required("member")
def home():
    user = current_user()
    mode = active_mode(user)
    db = get_db()
    data = get_pipeline_data()
    tabs = list_sessions(db, user["user_id"], mode)

    if mode == "Learning":
        sid = user["student_id"]
        student_row = db.fetch_one("SELECT * FROM students WHERE student_id = ?", (sid,))
        needs = db.fetch_all(
            "SELECT s.subject_id, s.subject_code, s.subject_name, ss.note "
            "FROM student_subjects ss JOIN subjects s ON s.subject_id = ss.subject_id "
            "WHERE ss.student_id = ? ORDER BY s.subject_code",
            (sid,),
        )
        # Suggested / Top Match tutors from pipeline
        matched_tutors = []
        pipeline_match = next((m for m in data["matches"] if m["student_id"] == sid), None)
        compatible_tids = [t for t, s in data["relation"] if s == sid]
        ordered_tids = []
        if pipeline_match:
            ordered_tids.append(pipeline_match["tutor_id"])
        for t in compatible_tids:
            if t not in ordered_tids:
                ordered_tids.append(t)

        for tid in ordered_tids[:2]:
            t_info = get_tutor_profile_data(db, tid)
            if not t_info:
                continue
            slots = common_slots(db, tid, sid)
            shared_subjs = sorted(
                set(r["subject_code"] for r in needs)
                & set(
                    r["subject_code"]
                    for r in db.fetch_all(
                        "SELECT s.subject_code FROM tutor_subjects ts "
                        "JOIN subjects s ON s.subject_id = ts.subject_id "
                        "WHERE ts.tutor_id = ?",
                        (tid,),
                    )
                )
            )
            matched_tutors.append({
                "tutor_id": tid,
                "profile": t_info["profile"],
                "rating": t_info["rating"],
                "slots": slots,
                "shared_subjects": shared_subjs,
                "is_top_match": pipeline_match and pipeline_match["tutor_id"] == tid,
                "remaining_spots": data["remaining"].get(tid, t_info["profile"]["capacity"]),
            })

        return render_template(
            "portal/home_student.html",
            student=student_row,
            needs=needs,
            tabs=tabs,
            matched_tutors=matched_tutors,
            today=datetime.now().strftime("%B %d, %Y"),
        )
    else:
        tid = user["tutor_id"]
        tutor_row = db.fetch_one("SELECT * FROM tutors WHERE tutor_id = ?", (tid,))
        teaches = db.fetch_all(
            "SELECT s.subject_id, s.subject_code, s.subject_name "
            "FROM tutor_subjects ts JOIN subjects s ON s.subject_id = ts.subject_id "
            "WHERE ts.tutor_id = ? ORDER BY s.subject_code",
            (tid,),
        )
        taken = db.fetch_one(
            "SELECT COUNT(DISTINCT student_id) AS n FROM sessions "
            "WHERE tutor_id = ? AND status = 'confirmed'",
            (tid,),
        )["n"]
        return render_template(
            "portal/home_tutor.html",
            tutor=tutor_row,
            teaches=teaches,
            tabs=tabs,
            taken=taken,
            today=datetime.now().strftime("%B %d, %Y"),
        )


# ---------------------------------------------------------------------------
# Member Portal: Match with Tutor / Classes
# ---------------------------------------------------------------------------
def _evaluate_student_tutors(db, sid, subject_code, data):
    """Return full matches (4/4) and almost-matches (3/4) for a student & subject."""
    svc = Services()
    try:
        tutors = db.fetch_all(
            "SELECT t.*, COALESCE(AVG(r.score), 0) AS avg_rating, "
            "COUNT(DISTINCT tr.review_id) AS review_count "
            "FROM tutors t "
            "LEFT JOIN tutor_reviews tr ON tr.tutor_id = t.tutor_id "
            "LEFT JOIN tutor_review_scores r ON r.review_id = tr.review_id "
            "WHERE t.verified = 1 "
            "GROUP BY t.tutor_id ORDER BY t.tutor_id"
        )
        recommended_tids = {
            m["tutor_id"]
            for m in data["matches"]
            if m["student_id"] == sid
            and (not data.get("multi_subject") or not subject_code or m.get("subject_code") == subject_code)
        }
        full_matches = []
        almost_matches = []

        for t in tutors:
            tid = t["tutor_id"]
            ev = svc.logic.evaluate(tid, sid)
            if not ev["not_self"]:
                continue
            t_subjs = svc.sets.get_tutor_subjects(tid)
            if subject_code and subject_code not in t_subjs:
                subj_ok = False
            else:
                subj_ok = ev["subject_match"]

            slots = common_slots(db, tid, sid, subject_code=subject_code) if ev["time_match"] else []
            remaining_spots = data["remaining"].get(tid, t["capacity"])
            cap_ok = remaining_spots > 0
            rules_met = sum([subj_ok, ev["time_match"], ev["language_match"], cap_ok])
            avg_rating = float(t["avg_rating"] or 0)

            t_langs = sorted(svc.sets.get_tutor_languages(tid))
            card = {
                "tutor": dict(t),
                "subjects": sorted(t_subjs),
                "languages": t_langs,
                "slots": slots,
                "slot_options": [
                    {
                        "date": d.isoformat(),
                        "label": f"{d.strftime('%a %b %d')} · {fmt12(sl['start_time'])}–{fmt12(sl['end_time'])}",
                        "start": sl["start_time"],
                        "end": sl["end_time"],
                    }
                    for sl in slots
                    for d in upcoming_dates(sl["day"], weeks=2)
                ],
                "subj_ok": subj_ok,
                "time_ok": ev["time_match"],
                "lang_ok": ev["language_match"],
                "cap_ok": cap_ok,
                "remaining_spots": remaining_spots,
                "avg_rating": avg_rating,
                "is_suggested": tid in recommended_tids,
                "rules_met": rules_met,
            }
            if subj_ok and ev["time_match"] and ev["language_match"] and cap_ok:
                full_matches.append(card)
            elif rules_met >= 2:
                almost_matches.append(card)
        full_matches.sort(
            key=lambda c: (not c["is_suggested"], -c["avg_rating"], -c["remaining_spots"])
        )
        almost_matches.sort(
            key=lambda c: (not c["subj_ok"], not c["time_ok"], not c["lang_ok"], not c["cap_ok"], -c["avg_rating"])
        )
        return full_matches, almost_matches
    finally:
        svc.close()


@app.route("/classes")
@login_required("member")
def classes_page():
    user = current_user()
    mode = active_mode(user)
    db = get_db()
    all_subjects = db.fetch_all("SELECT * FROM subjects ORDER BY subject_code")

    if mode == "Learning":
        sid = user["student_id"]
        needs = db.fetch_all(
            "SELECT s.subject_id, s.subject_code, s.subject_name, ss.note "
            "FROM student_subjects ss JOIN subjects s ON s.subject_id = ss.subject_id "
            "WHERE ss.student_id = ? ORDER BY s.subject_code",
            (sid,),
        )
        selected_id = request.args.get("subject_id", type=int)
        if not selected_id and needs:
            selected_id = needs[0]["subject_id"]
        selected_need = next((n for n in needs if n["subject_id"] == selected_id), None)

        data = get_pipeline_data()
        full_matches, almost_matches = [], []
        if selected_need:
            full_matches, almost_matches = _evaluate_student_tutors(
                db, sid, selected_need["subject_code"], data
            )

        need_ids = {n["subject_id"] for n in needs}
        available_subjects = [s for s in all_subjects if s["subject_id"] not in need_ids]

        return render_template(
            "portal/classes_student.html",
            needs=needs,
            selected_need=selected_need,
            available_subjects=available_subjects,
            full_matches=full_matches,
            almost_matches=almost_matches,
        )
    else:
        tid = user["tutor_id"]
        teaches = db.fetch_all(
            "SELECT s.subject_id, s.subject_code, s.subject_name "
            "FROM tutor_subjects ts JOIN subjects s ON s.subject_id = ts.subject_id "
            "WHERE ts.tutor_id = ? ORDER BY s.subject_code",
            (tid,),
        )
        teach_ids = {t["subject_id"] for t in teaches}
        available_subjects = [s for s in all_subjects if s["subject_id"] not in teach_ids]

        selected_id = request.args.get("subject_id", type=int)
        if not selected_id and teaches:
            selected_id = teaches[0]["subject_id"]
        selected_teach = next((t for t in teaches if t["subject_id"] == selected_id), None)

        avail_rows = db.fetch_all(
            "SELECT ta.availability_id, ta.subject_id, ta.day, ta.start_time, ta.end_time, "
            "s.subject_code, s.subject_name "
            "FROM tutor_availability ta "
            "LEFT JOIN subjects s ON s.subject_id = ta.subject_id "
            "WHERE ta.tutor_id = ? ORDER BY ta.day, ta.start_time",
            (tid,),
        )

        students_needing = []
        if selected_teach:
            students_needing = db.fetch_all(
                "SELECT st.student_id, st.name, st.course, st.grade_level, ss.note "
                "FROM student_subjects ss "
                "JOIN students st ON st.student_id = ss.student_id "
                "WHERE ss.subject_id = ? ORDER BY st.name",
                (selected_teach["subject_id"],),
            )

        return render_template(
            "portal/classes_tutor.html",
            teaches=teaches,
            selected_teach=selected_teach,
            available_subjects=available_subjects,
            students_needing=students_needing,
            avail_rows=avail_rows,
        )


@app.route("/classes/need/add", methods=["POST"])
@login_required("member")
def add_need_route():
    user = current_user()
    subject_id = request.form.get("subject_id", type=int)
    note = request.form.get("note", "")
    try:
        add_need(get_db(), user["user_id"], subject_id, note)
        flash("Class added to your learning list.", "success")
    except AuthError as err:
        flash(str(err), "error")
    return redirect(url_for("classes_page", subject_id=subject_id))


@app.route("/classes/need/delete", methods=["POST"])
@login_required("member")
def delete_need_route():
    user = current_user()
    subject_id = request.form.get("subject_id", type=int)
    remove_need(get_db(), user["user_id"], subject_id)
    flash("Class removed.", "success")
    return redirect(url_for("classes_page"))


@app.route("/classes/teach/add", methods=["POST"])
@login_required("member")
def add_teach_route():
    user = current_user()
    subject_id = request.form.get("subject_id", type=int)
    try:
        add_teach(get_db(), user["user_id"], subject_id)
        flash("Subject added to your tutoring list.", "success")
    except AuthError as err:
        flash(str(err), "error")
    return redirect(url_for("classes_page", subject_id=subject_id))


@app.route("/classes/teach/delete", methods=["POST"])
@login_required("member")
def delete_teach_route():
    user = current_user()
    subject_id = request.form.get("subject_id", type=int)
    remove_teach(get_db(), user["user_id"], subject_id)
    flash("Subject removed.", "success")
    return redirect(url_for("classes_page"))


# ---------------------------------------------------------------------------
# Member Portal: Calendar
# ---------------------------------------------------------------------------
def _build_calendar_events(db, user, mode, week_start, week_end):
    """Build weekly grid events (Mon-Sat, 7 AM - 6 PM) for the logged-in user."""
    events = []
    classes = []
    if user["student_id"] is not None:
        classes = db.fetch_all(
            "SELECT sc.schedule_id, sc.day, sc.start_time, sc.end_time, "
            "sub.subject_code, sub.subject_name "
            "FROM student_schedule sc JOIN subjects sub ON sub.subject_id = sc.subject_id "
            "WHERE sc.student_id = ? ORDER BY sc.day, sc.start_time",
            (user["student_id"],),
        )
        for c in classes:
            events.append({
                "kind": "class",
                "day": c["day"],
                "start": c["start_time"],
                "end": c["end_time"],
                "title": c["subject_name"],
                "subtitle": c["subject_code"],
            })

    avail_rows = []
    if mode == "Tutoring" and user["tutor_id"] is not None:
        avail_rows = db.fetch_all(
            "SELECT ta.availability_id, ta.subject_id, ta.day, ta.start_time, ta.end_time, "
            "s.subject_code, s.subject_name "
            "FROM tutor_availability ta "
            "LEFT JOIN subjects s ON s.subject_id = ta.subject_id "
            "WHERE ta.tutor_id = ? ORDER BY ta.day, ta.start_time",
            (user["tutor_id"],),
        )
        for a in avail_rows:
            events.append({
                "kind": "tutor-avail",
                "day": a["day"],
                "start": a["start_time"],
                "end": a["end_time"],
                "title": f"Tutor: {a['subject_name'].title()}" if a["subject_name"] else "Available to tutor",
                "subtitle": a["subject_code"] or f"{fmt12(a['start_time'])}–{fmt12(a['end_time'])}",
            })

    # Add upcoming/pending sessions that fall within the selected week
    tabs = list_sessions(db, user["user_id"], mode)
    for s in tabs["upcoming"]:
        s_date = datetime.strptime(s["session_date"], "%Y-%m-%d").date()
        if not (week_start <= s_date <= week_end):
            continue
        events.append({
            "kind": "session",
            "day": s_date.strftime("%A"),
            "start": s["start_time"],
            "end": s["end_time"],
            "title": s["subject_name"],
            "subtitle": f"with {s['tutor_name'] if mode == 'Learning' else s['student_name']}",
        })
    pending_list = tabs["sent"] if mode == "Learning" else tabs["reply"]
    for s in pending_list:
        s_date = datetime.strptime(s["session_date"], "%Y-%m-%d").date()
        if not (week_start <= s_date <= week_end):
            continue
        events.append({
            "kind": "pending",
            "day": s_date.strftime("%A"),
            "start": s["start_time"],
            "end": s["end_time"],
            "title": f"Pending: {s['subject_name']}",
            "subtitle": s["session_date"],
        })
    return events, classes, avail_rows


@app.route("/calendar")
@login_required("member")
def calendar_page():
    user = current_user()
    mode = active_mode(user)
    db = get_db()

    today_date = datetime.now().date()
    default_monday = today_date - timedelta(days=today_date.weekday())
    week_param = request.args.get("week")
    try:
        anchor = datetime.strptime(week_param, "%Y-%m-%d").date() if week_param else default_monday
    except ValueError:
        anchor = default_monday
    week_start = anchor - timedelta(days=anchor.weekday())
    week_end = week_start + timedelta(days=5)  # Saturday

    prev_week = (week_start - timedelta(days=7)).isoformat()
    next_week = (week_start + timedelta(days=7)).isoformat()
    today_week = default_monday.isoformat()

    month_label = week_start.strftime("%B %Y")
    if week_start.month == week_end.month:
        week_range_label = f"{week_start.strftime('%b %d')} – {week_end.strftime('%d, %Y')}"
    else:
        week_range_label = f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}"

    week_days = []
    for i, d_name in enumerate(DAYS):
        d_date = week_start + timedelta(days=i)
        week_days.append({
            "name": d_name,
            "short": d_name[:3],
            "num": d_date.day,
            "is_today": d_date == today_date,
        })

    events, classes, avail_rows = _build_calendar_events(db, user, mode, week_start, week_end)
    subjects = db.fetch_all("SELECT * FROM subjects ORDER BY subject_code")

    hours = list(range(7, 19))  # 7 AM to 6 PM
    positioned = {d: [] for d in DAYS}
    for ev in events:
        if ev["day"] not in positioned:
            continue
        start_m = max(7 * 60, to_minutes(ev["start"]))
        end_m = min(19 * 60, to_minutes(ev["end"]))
        if end_m <= start_m:
            continue
        ev["top_pct"] = ((start_m - 7 * 60) / (12 * 60)) * 100
        ev["height_pct"] = max(4.0, ((end_m - start_m) / (12 * 60)) * 100)
        positioned[ev["day"]].append(ev)

    return render_template(
        "portal/calendar.html",
        hours=hours,
        positioned=positioned,
        classes=classes,
        avail_rows=avail_rows,
        subjects=subjects,
        month_label=month_label,
        week_range_label=week_range_label,
        week_days=week_days,
        prev_week=prev_week,
        next_week=next_week,
        today_week=today_week,
    )


@app.route("/calendar/class/add", methods=["POST"])
@login_required("member")
def add_class_route():
    user = current_user()
    db = get_db()
    subject_id = request.form.get("subject_id", type=int)
    day = request.form.get("day", "")
    start = request.form.get("start_time", "")
    end = request.form.get("end_time", "")
    try:
        if user["student_id"] is None:
            add_profile(db, user["user_id"], "student")
        add_class(db, user["user_id"], subject_id, day, start, end)
        flash("Class added to your calendar.", "success")
    except AuthError as err:
        flash(str(err), "error")
    return redirect(url_for("calendar_page"))


@app.route("/calendar/class/delete", methods=["POST"])
@login_required("member")
def delete_class_route():
    user = current_user()
    schedule_id = request.form.get("schedule_id", type=int)
    delete_class(get_db(), user["user_id"], schedule_id)
    flash("Class removed from calendar.", "success")
    return redirect(url_for("calendar_page"))


@app.route("/calendar/availability/add", methods=["POST"])
@login_required("member")
def add_availability_route():
    user = current_user()
    subject_id = request.form.get("subject_id", type=int)
    day = request.form.get("day", "")
    start = request.form.get("start_time", "")
    end = request.form.get("end_time", "")
    try:
        add_availability(get_db(), user["user_id"], day, start, end, subject_id=subject_id)
        flash("Tutoring availability added.", "success")
    except AuthError as err:
        flash(str(err), "error")
    return redirect(request.referrer or url_for("classes_page"))


@app.route("/calendar/availability/delete", methods=["POST"])
@login_required("member")
def delete_availability_route():
    user = current_user()
    availability_id = request.form.get("availability_id", type=int)
    delete_availability(get_db(), user["user_id"], availability_id)
    flash("Availability removed.", "success")
    return redirect(request.referrer or url_for("classes_page"))


# ---------------------------------------------------------------------------
# Member Portal: Sessions
# ---------------------------------------------------------------------------
@app.route("/sessions")
@login_required("member")
def sessions_page():
    user = current_user()
    mode = active_mode(user)
    db = get_db()
    tabs = list_sessions(db, user["user_id"], mode)
    active_tab = request.args.get("tab", "pending")
    if active_tab not in ("pending", "upcoming", "history"):
        active_tab = "pending"
    return render_template(
        "portal/sessions.html",
        tabs=tabs,
        active_tab=active_tab,
    )


@app.route("/sessions/request", methods=["POST"])
@login_required("member")
def request_session_route():
    user = current_user()
    tutor_id = request.form.get("tutor_id", type=int)
    subject_id = request.form.get("subject_id", type=int)
    slot_value = request.form.get("slot", "")  # "YYYY-MM-DD|HH:MM|HH:MM"
    note = request.form.get("note", "")
    try:
        session_date, start, end = slot_value.split("|")
        request_session(
            get_db(), user["user_id"], tutor_id, subject_id,
            session_date, start, end, note
        )
        flash("Tutoring request sent!", "success")
        return redirect(url_for("sessions_page", tab="pending"))
    except (ValueError, AuthError) as err:
        flash(str(err), "error")
        return redirect(request.referrer or url_for("classes_page"))


@app.route("/sessions/<int:session_id>/respond", methods=["POST"])
@login_required("member")
def respond_session_route(session_id):
    user = current_user()
    accept = request.form.get("action") == "accept"
    try:
        respond_session(get_db(), user["user_id"], session_id, accept)
        flash("Session accepted!" if accept else "Request declined.", "success")
    except (AuthError, PermissionDenied) as err:
        flash(str(err), "error")
    return redirect(url_for("sessions_page", tab="upcoming" if accept else "history"))


@app.route("/sessions/<int:session_id>/cancel", methods=["POST"])
@login_required("member")
def cancel_session_route(session_id):
    user = current_user()
    try:
        cancel_session(get_db(), user["user_id"], session_id)
        flash("Session cancelled.", "success")
    except (AuthError, PermissionDenied) as err:
        flash(str(err), "error")
    return redirect(url_for("sessions_page"))


# ---------------------------------------------------------------------------
# Member Portal: People
# ---------------------------------------------------------------------------
@app.route("/people")
@login_required("member")
def people_page():
    db = get_db()
    tab = request.args.get("tab", "everyone")
    q = (request.args.get("q") or "").strip().lower()
    course_filter = (request.args.get("course") or "").strip()
    subject_filter = (request.args.get("subject") or "").strip()

    tutors = db.fetch_all(
        "SELECT t.tutor_id, t.name, t.course, t.grade_level, t.verified, "
        "GROUP_CONCAT(DISTINCT sub.subject_name) AS teaches, "
        "ROUND(AVG(rs.score), 1) AS rating "
        "FROM tutors t "
        "LEFT JOIN tutor_subjects ts ON ts.tutor_id = t.tutor_id "
        "LEFT JOIN subjects sub ON sub.subject_id = ts.subject_id "
        "LEFT JOIN tutor_reviews tr ON tr.tutor_id = t.tutor_id "
        "LEFT JOIN tutor_review_scores rs ON rs.review_id = tr.review_id "
        "WHERE t.verified = 1 "
        "GROUP BY t.tutor_id ORDER BY t.name"
    )
    students = db.fetch_all(
        "SELECT s.student_id, s.name, s.course, s.grade_level "
        "FROM students s "
        "WHERE s.student_id IN (SELECT DISTINCT student_id FROM student_subjects) "
        "ORDER BY s.name"
    )

    people_rows = []
    for t in tutors:
        people_rows.append({
            "kind": "tutor",
            "id": t["tutor_id"],
            "name": t["name"],
            "course": t["course"],
            "grade_level": t["grade_level"],
            "is_student": False,
            "is_tutor": True,
            "verified": bool(t["verified"]),
            "teaches": t["teaches"] or "—",
            "rating": t["rating"],
        })
    for s in students:
        people_rows.append({
            "kind": "student",
            "id": s["student_id"],
            "name": s["name"],
            "course": s["course"],
            "grade_level": s["grade_level"],
            "is_student": True,
            "is_tutor": False,
            "verified": True,
            "teaches": "—",
            "rating": None,
        })

    if tab == "tutors":
        people_rows = [p for p in people_rows if p["is_tutor"]]
    elif tab == "students":
        people_rows = [p for p in people_rows if p["is_student"]]
    if q:
        people_rows = [
            p for p in people_rows
            if q in p["name"].lower() or q in p["teaches"].lower() or q in p["course"].lower()
        ]
    if course_filter:
        people_rows = [p for p in people_rows if p["course"] == course_filter]
    if subject_filter:
        people_rows = [p for p in people_rows if subject_filter.lower() in p["teaches"].lower()]

    courses = sorted({p["course"] for p in people_rows if p["course"]})
    subjects = [r["subject_name"] for r in db.fetch_all("SELECT subject_name FROM subjects ORDER BY subject_name")]
    ratings = [t["rating"] for t in tutors if t["rating"] is not None]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else "—"

    return render_template(
        "portal/people.html",
        people=people_rows,
        tab=tab,
        q=q,
        course_filter=course_filter,
        subject_filter=subject_filter,
        courses=courses,
        subjects=subjects,
        total_people=len(tutors) + len(students),
        total_tutors=len(tutors),
        avg_rating=avg_rating,
    )


# ---------------------------------------------------------------------------
# Member Portal: Profile & Help
# ---------------------------------------------------------------------------
@app.route("/profile")
@login_required("member")
def my_profile():
    user = current_user()
    mode = active_mode(user)
    if mode == "Tutoring" and user["tutor_id"]:
        return redirect(url_for("tutor_profile", tutor_id=user["tutor_id"]))
    return redirect(url_for("student_profile", student_id=user["student_id"]))


@app.route("/profile/student/<int:student_id>")
@login_required("member")
def student_profile(student_id):
    user = current_user()
    db = get_db()
    pdata = get_student_profile_data(db, student_id)
    if not pdata:
        flash("Student profile not found.", "error")
        return redirect(url_for("people_page"))
    tab = request.args.get("tab", "about")
    if tab not in ("about", "info", "classes", "reviews", "certificates"):
        tab = "about"
    is_own = user["student_id"] == student_id
    owner_user = db.fetch_one("SELECT email, created_at FROM users WHERE student_id = ?", (student_id,))
    return render_template(
        "portal/profile.html",
        kind="student",
        pdata=pdata,
        tab=tab,
        is_own=is_own,
        owner_user=owner_user,
    )


@app.route("/profile/tutor/<int:tutor_id>")
@login_required("member")
def tutor_profile(tutor_id):
    user = current_user()
    db = get_db()
    pdata = get_tutor_profile_data(db, tutor_id)
    if not pdata:
        flash("Tutor profile not found.", "error")
        return redirect(url_for("people_page"))
    tab = request.args.get("tab", "about")
    if tab not in ("about", "info", "classes", "reviews", "certificates"):
        tab = "about"
    is_own = user["tutor_id"] == tutor_id
    owner_user = db.fetch_one("SELECT email, created_at FROM users WHERE tutor_id = ?", (tutor_id,))
    subjects = db.fetch_all(
        "SELECT s.subject_code, s.subject_name FROM tutor_subjects ts "
        "JOIN subjects s ON s.subject_id = ts.subject_id WHERE ts.tutor_id = ?",
        (tutor_id,),
    )
    availability = db.fetch_all(
        "SELECT day, start_time, end_time FROM tutor_availability "
        "WHERE tutor_id = ? ORDER BY day, start_time",
        (tutor_id,),
    )
    languages = [
        r["language"]
        for r in db.fetch_all("SELECT language FROM tutor_languages WHERE tutor_id = ?", (tutor_id,))
    ]
    return render_template(
        "portal/profile.html",
        kind="tutor",
        pdata=pdata,
        tab=tab,
        is_own=is_own,
        owner_user=owner_user,
        tutor_subjects=subjects,
        tutor_availability=availability,
        tutor_languages=languages,
    )


@app.route("/profile/settings", methods=["POST"])
@login_required("member")
def update_profile_settings():
    user = current_user()
    mode = active_mode(user)
    db = get_db()
    kind = "student" if mode == "Learning" else "tutor"
    langs = request.form.getlist("languages")
    try:
        if langs:
            set_languages(db, user["user_id"], kind, langs)
        if kind == "tutor" and request.form.get("capacity"):
            set_capacity(db, user["user_id"], int(request.form.get("capacity")))
        flash("Profile preferences updated.", "success")
    except (AuthError, ValueError) as err:
        flash(str(err), "error")
    return redirect(request.referrer or url_for("my_profile"))


@app.route("/help")
@login_required("member")
def help_page():
    return render_template("portal/help.html")


# ---------------------------------------------------------------------------
# Administrator / Discrete Math Portal Routes
# ---------------------------------------------------------------------------
@app.route("/admin")
@login_required("admin")
def admin_root():
    return redirect(url_for("admin_home"))


@app.route("/admin/home")
@login_required("admin")
def admin_home():
    data = get_pipeline_data()
    n_students = len(data["student_ids"])
    n_tutors = len(data["tutor_ids"])
    n_matched = len(data["matches"])
    n_waiting = len(data["unmatched"])
    unverified = data["tutors"][~data["tutors"]["verified"]].to_dict("records")
    sname = dict(zip(data["students"]["student_id"], data["students"]["name"]))
    unmatched_list = [
        {
            "name": sname.get(u["student_id"], f"Student #{u['student_id']}"),
            "reason": (
                "Compatible tutors are already at full capacity."
                if u["has_compatible"]
                else "No tutor teaches the subject, matches language, and shares free time."
            ),
        }
        for u in data["unmatched"]
    ]
    return render_template(
        "admin/home.html",
        n_students=n_students,
        n_tutors=n_tutors,
        n_matched=n_matched,
        n_waiting=n_waiting,
        unverified=unverified,
        unmatched_list=unmatched_list,
    )


@app.route("/admin/matches")
@login_required("admin")
def admin_matches():
    data = get_pipeline_data()
    tname = dict(zip(data["tutors"]["tutor_id"], data["tutors"]["name"]))
    sname = dict(zip(data["students"]["student_id"], data["students"]["name"]))
    match_rows = [
        {
            "student": sname.get(m["student_id"]),
            "tutor": tname.get(m["tutor_id"]),
            "subjects": ", ".join(data["subject_names"].get(c, c) for c in m["shared"]),
            "times": ", ".join(fmt_range(sl) for sl in m["slots"]) or "—",
        }
        for m in data["matches"]
    ]
    assigned = Counter(t for t, _ in data["pairs"])
    tutor_load = [
        {
            "name": r["name"],
            "assigned": assigned[r["tutor_id"]],
            "remaining": data["remaining"][r["tutor_id"]],
            "capacity": data["capacities"][r["tutor_id"]],
        }
        for _, r in data["tutors"].iterrows()
    ]
    unmatched_rows = [
        {
            "name": sname.get(u["student_id"]),
            "reason": (
                "Compatible tutors are at full capacity."
                if u["has_compatible"]
                else "No compatible tutor (subject, schedule, or language mismatch)."
            ),
        }
        for u in data["unmatched"]
    ]
    return render_template(
        "admin/matches.html",
        match_rows=match_rows,
        tutor_load=tutor_load,
        unmatched_rows=unmatched_rows,
    )


@app.route("/admin/people")
@login_required("admin")
def admin_people():
    data = get_pipeline_data()
    kind = request.args.get("kind", "students")
    if kind not in ("students", "tutors"):
        kind = "students"
    rows = data[kind].to_dict("records")
    return render_template("admin/people.html", kind=kind, rows=rows)


@app.route("/admin/inspector")
@login_required("admin")
def admin_inspector():
    data = get_pipeline_data()
    tutors = data["tutors"].to_dict("records")
    students = data["students"].to_dict("records")
    tid = request.args.get("tutor_id", type=int) or (tutors[0]["tutor_id"] if tutors else None)
    sid = request.args.get("student_id", type=int) or (students[0]["student_id"] if students else None)

    report = None
    if tid and sid:
        svc = Services()
        try:
            report = svc.logic.evaluate(tid, sid)
        finally:
            svc.close()

    return render_template(
        "admin/inspector.html",
        tutors=tutors,
        students=students,
        selected_tid=tid,
        selected_sid=sid,
        report=report,
    )


@app.route("/admin/accounts", methods=["GET", "POST"])
@login_required("admin")
def admin_accounts():
    user = current_user()
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "toggle_active":
                target_id = request.form.get("target_user_id", type=int)
                active = request.form.get("active") == "1"
                set_account_active(db, user["user_id"], target_id, active)
                flash("Account status updated.", "success")
            elif action == "toggle_verify":
                tutor_id = request.form.get("tutor_id", type=int)
                verified = request.form.get("verified") == "1"
                set_tutor_verified(db, user["user_id"], tutor_id, verified)
                flash("Tutor verification updated.", "success")
        except (AuthError, PermissionDenied) as err:
            flash(str(err), "error")
        return redirect(url_for("admin_accounts"))

    accounts = list_accounts(db, user["user_id"])
    tutors = db.fetch_all("SELECT tutor_id, name, course, grade_level, verified FROM tutors ORDER BY tutor_id")
    return render_template("admin/accounts.html", accounts=accounts, tutors=tutors)


@app.route("/admin/settings", methods=["GET", "POST"])
@login_required("admin")
def admin_settings():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "capacity":
            session["cap_mode"] = request.form.get("cap_mode", "stored")
            try:
                session["cap_uniform"] = max(1, int(request.form.get("cap_uniform", 1)))
            except ValueError:
                session["cap_uniform"] = 1
            flash("Matching capacity settings saved.", "success")
        return redirect(url_for("admin_settings"))

    return render_template(
        "admin/settings.html",
        cap_mode=session.get("cap_mode", "stored"),
        cap_uniform=session.get("cap_uniform", 1),
    )


@app.route("/admin/toggle-multi-subject", methods=["POST"])
@login_required("admin")
def admin_toggle_multi_subject():
    enabled = request.form.get("multi_subject") == "1"
    set_multi_subject_mode(enabled)
    return redirect(request.referrer or url_for("admin_matching_works"))


@app.route("/admin/matching-works")
@login_required("admin")
def admin_matching_works():
    data = get_pipeline_data()
    multi_subject = data.get("multi_subject", False)
    t_count = len(data["tutor_ids"])
    right_count = len(data["right_ids"])
    rel_count = len(data["graph_relation"])
    match_count = len(data["pairs"])
    ver = data["verification"]

    # Mathematical invariants / safety checks
    rel_set = set(data["graph_relation"])
    r_deg = Counter(r for _, r in data["pairs"])
    t_deg = Counter(t for t, _ in data["pairs"])
    total_cap = sum(data["capacities"].values())
    max_possible = min(right_count, total_cap)

    deg_label = (
        "No student has more than one tutor per subject (deg(s, subj) ≤ 1)"
        if multi_subject
        else "No student has more than one tutor (deg(s) ≤ 1)"
    )
    cap_bound_label = (
        "Matches never exceed what is possible (|M| ≤ min(|S'|, Σc))"
        if multi_subject
        else "Matches never exceed what is possible (|M| ≤ min(|S|, Σc))"
    )

    checks = [
        ("Every match is a compatible pair (M ⊆ R)", all((t, r) in rel_set for t, r in data["pairs"])),
        (deg_label, all(d <= 1 for d in r_deg.values())),
        ("No tutor is over their limit (deg(t) ≤ c)", all(t_deg[t] <= data["capacities"][t] for t in data["tutor_ids"])),
        (cap_bound_label, match_count <= max_possible),
        ("The graph has two separate sides (Bipartite)", ver.get("partitions_valid", False)),
        ("The graph's lines equal the compatible pairs (|E| = |R|)", ver.get("edges_valid", False)),
    ]

    return render_template(
        "admin/matching_works.html",
        total_pairs=t_count * right_count,
        rel_count=rel_count,
        match_count=match_count,
        checks=checks,
        multi_subject=multi_subject,
    )


@app.route("/admin/graph.png")
@login_required("admin")
def admin_graph_png():
    data = get_pipeline_data()
    kind = request.args.get("kind", "compatibility")
    vis = TUGMAVisualizer()
    if kind == "selected":
        fig = vis.draw_after_matching(data["graph"], data["pairs"])
    else:
        fig = vis.draw_before_matching(data["graph"])

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="#FFFFFF")
    plt.close(fig)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype="image/png")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
