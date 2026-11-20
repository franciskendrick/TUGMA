"""Tutor profile page: academic details, teaching ratings, and certificates."""

import html

import streamlit as st

from services.migrations import DB_PATH
from services.profile_service import (
    get_profile_tabs,
    get_student_profile_data,
    get_tutor_profile_data,
)
from src.database import Database
from views.components import initials


def _safe(value):
    return html.escape(str(value or ""))


def render_profile(user, active_mode="Learning"):
    """Render the profile matching the currently selected Learning/Tutoring mode."""
    st.title("Profile")
    if active_mode == "Tutoring":
        if user.get("tutor_id") is None:
            st.info("This account does not have a tutor profile. Select Learning mode or add a tutor profile from Home.")
            return
        _render_tutor_profile(user)
        return

    if user.get("student_id") is None:
        st.info("This account does not have a student profile. Select Tutoring mode or add a student profile from Home.")
        return
    _render_student_profile(user)


def _render_student_profile(user):
    """Render the student-facing profile. Student tabs intentionally exclude tutor features."""
    db = Database(DB_PATH)
    try:
        data = get_student_profile_data(db, user["student_id"])
    finally:
        db.close()

    if not data:
        st.error("Student profile not found.")
        return

    profile = data["profile"]
    name = profile["name"]
    course = profile.get("course") or "Program not specified"
    year = profile.get("grade_level")
    year_label = f"Year {year}" if year is not None else "Year level not specified"
    active = profile.get("is_active")
    account_status = "Active account" if active == 1 else (
        "Inactive account" if active == 0 else "No linked account record"
    )

    st.markdown(
        f"""<div class="tg-profile-hero">
          <div class="tg-profile-avatar">{_safe(initials(name))}</div>
          <div class="tg-profile-identity">
            <div class="tg-profile-role">Student · Learning</div>
            <h2>{_safe(name)}</h2>
            <p>{_safe(course)} student</p>
            <span class="tg-profile-verified">✓ Student profile</span>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )

    account_col, academic_col = st.columns([1, 1.5])
    with account_col:
        with st.container(border=True):
            st.subheader("Account")
            st.write(f"**Status:** {account_status}")
            st.write(f"**Email:** {profile.get('email') or 'Not linked'}")
            st.write(f"**Joined:** {profile.get('created_at') or 'Not available'}")
    with academic_col:
        with st.container(border=True):
            st.subheader("Academic profile")
            st.write("**De La Salle University – Dasmariñas**")
            st.write(f"{_safe(course)} · {_safe(year_label)}")

    about, info, classes = st.tabs(list(get_profile_tabs("Learning")))
    with about:
        st.subheader("About")
        st.write(profile.get("bio") or "This student has not added a biography yet.")
        st.subheader("Study notes")
        st.write(profile.get("study_notes") or "No study preferences or learning notes have been added yet.")
        st.subheader("Interests")
        st.write(profile.get("interests") or "No interests have been added yet.")

    with info:
        st.subheader("Academic information")
        c1, c2 = st.columns(2)
        c1.metric("Program / course", course)
        c2.metric("Year level", str(year) if year is not None else "—")
        st.write("**School**")
        st.write("De La Salle University – Dasmariñas")
        st.write("**Department**")
        st.write("Not specified in the current student record.")
        st.write("**Languages**")
        st.write(", ".join(data["languages"]) or "No languages specified.")
        st.write("**Account status**")
        st.write(account_status)

    with classes:
        st.subheader("Registered subjects")
        if data["subjects"]:
            for subject in data["subjects"]:
                st.markdown(
                    f"- **{_safe(subject['subject_code'])}** · {_safe(subject['subject_name'].title())}"
                )
                if subject.get("note"):
                    st.caption(f"Study note: {_safe(subject['note'])}")
        else:
            st.info("No subjects have been added to this student's learning profile.")

        st.subheader("Weekly class schedule")
        if data["schedule"]:
            st.dataframe(
                [
                    {
                        "Day": row["day"],
                        "Time": f"{row['start_time']}–{row['end_time']}",
                        "Subject": f"{row['subject_code']} · {row['subject_name'].title()}",
                    }
                    for row in data["schedule"]
                ],
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("No weekly class schedule has been registered.")


def _render_tutor_profile(user):
    """Render the existing tutor profile without changing its tutor-only tabs."""

    db = Database(DB_PATH)
    try:
        data = get_tutor_profile_data(db, user["tutor_id"])
        subjects = db.fetch_all(
            """SELECT s.subject_code, s.subject_name
               FROM tutor_subjects ts JOIN subjects s USING (subject_id)
               WHERE ts.tutor_id=? ORDER BY s.subject_code""",
            (user["tutor_id"],),
        )
        availability = db.fetch_all(
            "SELECT day, start_time, end_time FROM tutor_availability "
            "WHERE tutor_id=? ORDER BY CASE day WHEN 'Monday' THEN 1 "
            "WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 "
            "WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 ELSE 7 END, start_time",
            (user["tutor_id"],),
        )
        languages = db.fetch_all(
            "SELECT language FROM tutor_languages WHERE tutor_id=? ORDER BY language",
            (user["tutor_id"],),
        )
    finally:
        db.close()

    if not data:
        st.error("Tutor profile not found.")
        return

    profile = data["profile"]
    rating = data["rating"]
    certificates = data["certificates"]
    name = profile["name"]
    verification = "Verified tutor" if profile["verified"] else "Unverified tutor"

    st.markdown(
        f"""<div class="tg-profile-hero">
          <div class="tg-profile-avatar">{_safe(initials(name))}</div>
          <div class="tg-profile-identity">
            <div class="tg-profile-role">Student · Peer tutor</div>
            <h2>{_safe(name)}</h2>
            <p>{_safe(profile['course'])} student · Peer tutor</p>
            <span class="tg-profile-verified">{'✓' if profile['verified'] else '○'} {_safe(verification)}</span>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )

    account_col, trust_col = st.columns([2.1, 1])
    with account_col:
        st.markdown(f"**De La Salle University – Dasmariñas**  \n{_safe(profile['course'])} · Year {profile['grade_level']}")
    with trust_col:
        st.metric("Teaching rating", f"{rating['overall']:.1f} / 5" if rating["overall"] is not None else "—")
        st.caption(f"{rating['rated_sessions']} rated sessions · {rating['rated_students']} students")

    st.divider()
    about, info, classes, reviews, awards = st.tabs(
        ["About", "Info", "Classes", "Reviews", "Certificates"]
    )
    with about:
        st.subheader("About")
        st.write(f"{name} is a peer tutor at De La Salle University – Dasmariñas.")
        st.caption("Tutor profile information is managed through the TUGMA account and tutoring profile.")
    with info:
        st.subheader("Academic information")
        c1, c2, c3 = st.columns(3)
        c1.metric("Course", profile["course"])
        c2.metric("Year level", profile["grade_level"])
        c3.metric("Student capacity", profile["capacity"])
        st.write("**Languages**")
        st.write(", ".join(row["language"] for row in languages) or "Not specified")
    with classes:
        st.subheader("Tutoring subjects")
        if subjects:
            for row in subjects:
                st.markdown(f"- **{_safe(row['subject_code'])}** · {_safe(row['subject_name'].title())}")
        else:
            st.info("No tutoring subjects have been added.")
        st.subheader("Weekly availability")
        if availability:
            st.dataframe(
                [{"Day": r["day"], "Available": f"{r['start_time']}–{r['end_time']}"} for r in availability],
                hide_index=True, use_container_width=True,
            )
        else:
            st.info("No availability has been added.")
    with reviews:
        _render_rating(rating)
    with awards:
        _render_certificates(certificates)

    if any(row["is_demo"] for row in _demo_review_flags(user["tutor_id"])):
        st.caption("Demonstration data: seeded ratings are sample records, not genuine student feedback.")


def _demo_review_flags(tutor_id):
    db = Database(DB_PATH)
    try:
        return db.fetch_all("SELECT is_demo FROM tutor_reviews WHERE tutor_id=?", (tutor_id,))
    finally:
        db.close()


def _render_rating(rating):
    st.subheader("Teaching rating")
    st.caption("Criterion averages from submitted tutor reviews.")
    left, right = st.columns([1, 2.2])
    with left:
        overall = rating["overall"]
        st.markdown(f"<div class='tg-rating-number'>{f'{overall:.1f}' if overall is not None else '—'}</div>", unsafe_allow_html=True)
        st.write(f"{rating['rated_sessions']} rated sessions · {rating['rated_students']} students")
    with right:
        if not rating["criteria"]:
            st.info("No teaching reviews yet.")
        for row in rating["criteria"]:
            score = row["average_rating"]
            st.markdown(f"**{_safe(row['criterion'])}** · {score:.1f} / 5")
            st.progress(min(1.0, score / 5))


def _render_certificates(certificates):
    st.subheader("Certificates")
    earned = sum(row["status"] == "earned" for row in certificates)
    active = len(certificates) - earned
    st.caption(f"{earned} earned · {active} in progress")
    if not certificates:
        st.info("No certificates have been awarded yet.")
        return

    cols = st.columns(2)
    for index, item in enumerate(certificates):
        with cols[index % 2]:
            with st.container(border=True):
                tier = item["tier"] or ("In progress" if item["status"] == "in_progress" else "Earned")
                st.markdown(f"**{_safe(item['title'])}**")
                st.caption(f"{_safe(tier)} certificate · {_safe(item['category'].title())}")
                st.write(item["description"])
                if item["status"] == "earned":
                    st.success(f"Earned {item['earned_date']}")
                else:
                    st.caption(item["requirement_label"])
                    st.progress(item["progress_percent"] / 100)
                    st.caption(f"{item['progress_value']} of {item['target_value']} completed")
