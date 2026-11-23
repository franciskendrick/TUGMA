"""Tutor profile page: academic details, teaching ratings, and certificates.

Renders a card-based layout that matches the design references:
  - Green hero banner with an overlapping circular avatar
  - Role badge, verified chip, "Edit profile" pill
  - Segmented, clickable tab bar (About / Info / Classes / Reviews / Certificates)
  - Right-hand "Account" and "Trust Signals" cards
  - About / Hobbies / How-I-study rendered as bordered cards
  - Rating breakdown with inline progress bars
  - Certificate grid with earned / in-progress states

Tabs are built from real st.button widgets so clicks actually switch
content (raw HTML spans cannot receive Streamlit click events).
"""

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


# ----------------------------------------------------------------- helpers
def _safe(value):
    return html.escape(str(value or ""))


def _split_tags(raw):
    return [t.strip() for t in (raw or "").split(",") if t.strip()]


def _chip(text, kind="neutral"):
    return f'<span class="tg-chip tg-{kind}">{_safe(text)}</span>'


def _segmented_tabs(options, key, default=None):
    """Render a working pill-style tab bar and return the selected label.

    Uses one st.button per tab (real clicks) plus session state so the bar
    matches the design references while remaining functional.
    """
    if default is None:
        default = options[0]
    state_key = f"_tab_{key}"
    st.session_state.setdefault(state_key, default)

    # Guard against a stale selection if the option list ever changes.
    if st.session_state[state_key] not in options:
        st.session_state[state_key] = default

    cols = st.columns(len(options), gap="small")
    for col, label in zip(cols, options):
        active = st.session_state[state_key] == label
        cls = "tg-tab-btn tg-tab-btn-active" if active else "tg-tab-btn"
        with col:
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(label, key=f"{state_key}_{label}", use_container_width=True):
                st.session_state[state_key] = label
            st.markdown("</div>", unsafe_allow_html=True)

    return st.session_state[state_key]


def _hero(name, role, subtitle, verified_label=None, verified_ok=True, edit=False):
    """Green banner + overlapping avatar + identity block."""
    safe_name = _safe(name)
    safe_role = _safe(role)
    safe_sub = _safe(subtitle)
    verified = ""
    if verified_label:
        mark = "✓" if verified_ok else "○"
        verified = (
            f'<span class="tg-hero-chip tg-hero-chip-ok">'
            f"{mark} {_safe(verified_label)}</span>"
        )
    edit_html = (
        '<div class="tg-hero-action">'
        '<button class="tg-btn tg-btn-primary tg-btn-pill" type="button">'
        '✎ Edit profile</button></div>'
        if edit
        else ""
    )
    st.markdown(
        f"""
        <div class="tg-profile-hero-wrap">
          <div class="tg-profile-hero-banner">
            <span class="tg-hero-role">{safe_role}</span>
          </div>
          <div class="tg-profile-hero-body">
            <div class="tg-profile-avatar-lg">{_safe(initials(name))}</div>
            <div class="tg-profile-hero-info">
              <h1 class="tg-profile-hero-name">{safe_name}</h1>
              <p class="tg-profile-hero-sub">{safe_sub}</p>
              {verified}
            </div>
            {edit_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _account_card(profile, show_logout=False):
    email = profile.get("email") or "Not linked"
    joined = profile.get("created_at") or "Not available"
    joined = str(joined)[:10] if joined != "Not available" else joined
    logout = (
        '<button class="tg-btn tg-btn-outline tg-btn-pill tg-btn-block" '
        'type="button">↪ Log out</button>'
        if show_logout
        else ""
    )
    st.markdown(
        f"""
        <div class="tg-side-card">
          <div class="tg-side-card-head">👤 <span>Account</span></div>
          <div class="tg-side-row"><span class="tg-side-label">Joined</span>{_safe(joined)}</div>
          <div class="tg-side-row"><span class="tg-side-label">Microsoft 365 account</span>
            <span class="tg-side-mono">{_safe(email)}</span></div>
          {logout}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _trust_card(rows):
    body = "".join(
        f'<div class="tg-side-row"><span class="tg-side-ico">{ico}</span>'
        f"<span>{_safe(label)}</span></div>"
        for ico, label in rows
    )
    st.markdown(
        f"""
        <div class="tg-side-card">
          <div class="tg-side-card-head">🛡️ <span>Trust Signals</span></div>
          {body}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _card(title, body_html, edit=False):
    edit_html = (
        '<button class="tg-link-edit" type="button">✎ Edit</button>' if edit else ""
    )
    st.markdown(
        f"""
        <div class="tg-card">
          <div class="tg-card-head"><h3>{_safe(title)}</h3>{edit_html}</div>
          {body_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- routing
def render_profile(user, active_mode="Learning"):
    """Render the profile matching the currently selected Learning/Tutoring mode."""
    if active_mode == "Tutoring":
        if user.get("tutor_id") is None:
            st.info(
                "This account does not have a tutor profile. Select Learning "
                "mode or add a tutor profile from Home."
            )
            return
        _render_tutor_profile(user)
        return

    if user.get("student_id") is None:
        st.info(
            "This account does not have a student profile. Select Tutoring "
            "mode or add a student profile from Home."
        )
        return
    _render_student_profile(user)


# ------------------------------------------------------- student profile
def _render_student_profile(user):
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
    course_line = f"{course}{year}" if year else course
    active = profile.get("is_active")
    account_status = (
        "Active account"
        if active == 1
        else "Inactive account"
        if active == 0
        else "No linked account record"
    )

    _hero(
        name=name,
        role="Student · Learning",
        subtitle=f"{course_line} · learns best from worked examples",
        verified_label="Verified student",
        verified_ok=True,
        edit=True,
    )

    main, side = st.columns([2.4, 1], gap="large")

    with side:
        _account_card(profile)
        _trust_card(
            [
                ("🎓", f"{len(data['subjects'])} Tutoring Subject"
                      + ("s" if len(data["subjects"]) != 1 else "")),
            ]
        )

    with main:
        selected = _segmented_tabs(
            ["About", "Info", "Classes", "Reviews"],
            key="student_profile",
            default="About",
        )

        if selected == "About":
            _card(
                "About",
                f'<p class="tg-body-text">{_safe(profile.get("bio") or "No biography yet.")}</p>',
                edit=True,
            )

            tags = _split_tags(profile.get("interests"))
            tags_html = (
                "".join(
                    f'<span class="tg-tag">{_safe(t)} <span class="tg-tag-x">×</span></span>'
                    for t in tags
                )
                or '<span class="tg-muted">No interests yet.</span>'
            )
            _card(
                "Hobbies and interests",
                f'<div class="tg-tag-row">{tags_html}</div>'
                '<div class="tg-add-row">'
                '<input class="tg-input" placeholder="Add a hobby, e.g. Chess" />'
                '<button class="tg-btn tg-btn-outline tg-btn-pill" type="button">+ Add</button>'
                "</div>",
            )

            rows = [
                ("Learning style", profile.get("learning_style") or "Not specified"),
                ("Preferred setup", profile.get("preferred_setup") or "Not specified"),
                ("Free time", profile.get("free_time") or "Not specified"),
            ]
            body = "".join(
                f'<div class="tg-kv-row"><span class="tg-kv-key">{_safe(k)}</span>'
                f'<span class="tg-kv-val">{_safe(v)}</span></div>'
                for k, v in rows
            )
            _card("How I study", body)

            _card(
                "Study notes",
                f'<p class="tg-body-text">{_safe(profile.get("study_notes") or "No study preferences yet.")}</p>',
            )

        elif selected == "Info":
            st.markdown("**Academic information**")
            c1, c2 = st.columns(2)
            c1.metric("Program / course", course)
            c2.metric("Year level", str(year) if year is not None else "—")
            st.write("**Languages**  \n" + (", ".join(data["languages"]) or "Not specified"))
            st.write("**Account status**  \n" + account_status)

        elif selected == "Classes":
            st.markdown("**Registered subjects**")
            if data["subjects"]:
                for s in data["subjects"]:
                    st.markdown(
                        f"- **{_safe(s['subject_code'])}** · "
                        f"{_safe(s['subject_name'].title())}"
                    )
            else:
                st.caption("No subjects have been added yet.")

            st.markdown("**Weekly class schedule**")
            if data["schedule"]:
                st.dataframe(
                    [
                        {
                            "Day": r["day"],
                            "Time": f"{r['start_time']}–{r['end_time']}",
                            "Subject": f"{r['subject_code']} · {r['subject_name'].title()}",
                        }
                        for r in data["schedule"]
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.caption("No weekly class schedule has been registered.")

        elif selected == "Reviews":
            st.info(
                "Student profiles do not collect teaching reviews. "
                "Switch to Tutoring mode to see tutor reviews."
            )


# --------------------------------------------------------- tutor profile
def _render_tutor_profile(user):
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

    subject_phrase = (
        " · peer tutor for " + ", ".join(r["subject_name"].title() for r in subjects)
        if subjects
        else ""
    )
    _hero(
        name=name,
        role="Student · Peer tutor",
        subtitle=f"{profile['course']}{profile['grade_level']}{subject_phrase}",
        verified_label=verification,
        verified_ok=bool(profile["verified"]),
        edit=True,
    )

    main, side = st.columns([2.4, 1], gap="large")

    with side:
        _account_card(profile)
        _trust_card(
            [
                ("📚", f"{len(subjects)} Tutoring Subject"
                      + ("s" if len(subjects) != 1 else "")),
                (
                    "⭐",
                    f"{rating['overall']:.1f} teaching rating · "
                    f"{rating['rated_sessions']} sessions"
                    if rating["overall"] is not None
                    else "No ratings yet",
                ),
                (
                    "🏅",
                    f"{sum(1 for c in certificates if c['status'] == 'earned')} "
                    f"certificates earned",
                ),
            ]
        )

    with main:
        selected = _segmented_tabs(
            ["About", "Info", "Classes", "Reviews", "Certificates"],
            key="tutor_profile",
            default="About",
        )

        if selected == "About":
            st.markdown(
                f"{_safe(name)} is a peer tutor at De La Salle University – Dasmariñas."
            )
            st.caption(
                "Tutor profile information is managed through the TUGMA account "
                "and tutoring profile."
            )

        elif selected == "Info":
            c1, c2, c3 = st.columns(3)
            c1.metric("Course", profile["course"])
            c2.metric("Year level", profile["grade_level"])
            c3.metric("Student capacity", profile["capacity"])
            st.write(
                "**Languages**  \n"
                + (", ".join(r["language"] for r in languages) or "Not specified")
            )

        elif selected == "Classes":
            st.markdown("**Tutoring subjects**")
            if subjects:
                for r in subjects:
                    st.markdown(
                        f"- **{_safe(r['subject_code'])}** · "
                        f"{_safe(r['subject_name'].title())}"
                    )
            else:
                st.caption("No tutoring subjects have been added.")

            st.markdown("**Weekly availability**")
            if availability:
                st.dataframe(
                    [
                        {"Day": r["day"],
                         "Available": f"{r['start_time']}–{r['end_time']}"}
                        for r in availability
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.caption("No availability has been added.")

        elif selected == "Reviews":
            _render_rating(rating)

        elif selected == "Certificates":
            _render_certificates(certificates)

    if any(row["is_demo"] for row in _demo_review_flags(user["tutor_id"])):
        st.caption(
            "Demonstration data: seeded ratings are sample records, not genuine "
            "student feedback."
        )


def _demo_review_flags(tutor_id):
    db = Database(DB_PATH)
    try:
        return db.fetch_all("SELECT is_demo FROM tutor_reviews WHERE tutor_id=?", (tutor_id,))
    finally:
        db.close()


# -------------------------------------------------------- rating section
def _render_rating(rating):
    st.markdown("**Teaching rating**")
    st.caption("From verified students after each session. Only students who attended can rate.")

    overall = rating["overall"]
    left, right = st.columns([1, 2.6])
    with left:
        st.markdown(
            f'<div class="tg-rating-overall">{f"{overall:.1f}" if overall is not None else "—"}</div>'
            '<div class="tg-rating-stars">★★★★★</div>'
            f'<div class="tg-muted">{rating["rated_sessions"]} rated sessions · '
            f'{rating["rated_students"]} students</div>',
            unsafe_allow_html=True,
        )
    with right:
        if not rating["criteria"]:
            st.info("No teaching reviews yet.")
        for row in rating["criteria"]:
            score = row["average_rating"]
            pct = min(100, (score / 5) * 100)
            st.markdown(
                f'<div class="tg-rating-row">'
                f'<span class="tg-rating-label">{_safe(row["criterion"])}</span>'
                f'<div class="tg-rating-bar"><span style="width:{pct:.0f}%"></span></div>'
                f'<span class="tg-rating-score">{score:.1f}</span>'
                "</div>",
                unsafe_allow_html=True,
            )


# ------------------------------------------------------- certificate grid
def _cert_card(item):
    tier = item["tier"] or ("In progress" if item["status"] == "in_progress" else "Earned")
    if item["status"] == "earned":
        footer = (
            f'<div class="tg-cert-footer tg-cert-earned">'
            f'<span class="tg-check">✓</span> Earned {_safe(item["earned_date"])}</div>'
        )
    else:
        pct = item["progress_percent"]
        footer = (
            f'<div class="tg-cert-req">{_safe(item["requirement_label"])}</div>'
            f'<div class="tg-cert-bar"><span style="width:{pct}%"></span></div>'
            f'<div class="tg-cert-progress">'
            f'{item["progress_value"]} of {item["target_value"]} completed</div>'
        )
    medal_class = (
        "tg-medal-gold" if tier == "Gold"
        else "tg-medal-silver" if tier == "Silver"
        else "tg-medal-bronze" if tier == "Bronze"
        else "tg-medal-muted"
    )
    return (
        f'<div class="tg-cert-card">'
        f'<div class="tg-cert-head">'
        f'<span class="tg-medal {medal_class}">🏅</span>'
        f'<div><div class="tg-cert-title">{_safe(item["title"])}</div>'
        f'<div class="tg-cert-tier">{_safe(tier)} certificate</div></div>'
        f"</div>"
        f'<div class="tg-cert-desc">{_safe(item["description"])}</div>'
        f"{footer}"
        f"</div>"
    )


def _render_certificates(certificates):
    earned = sum(1 for c in certificates if c["status"] == "earned")
    active = len(certificates) - earned

    legend = (
        '<span class="tg-tier-pill tg-tier-bronze">Bronze 5+</span>'
        '<span class="tg-tier-pill tg-tier-silver">Silver 10+</span>'
        '<span class="tg-tier-pill tg-tier-gold">Gold 20+ ratings at 4.5★ or higher</span>'
    )
    st.markdown(
        f'<div class="tg-cert-section-head">'
        f"<h3>Certificates</h3>"
        f'<div class="tg-cert-count">{earned} earned · {active} in progress</div>'
        f"</div>"
        f'<div class="tg-tier-legend">{legend}</div>',
        unsafe_allow_html=True,
    )

    if not certificates:
        st.info("No certificates have been awarded yet.")
        return

    cards = "".join(_cert_card(c) for c in certificates)
    st.markdown(f'<div class="tg-cert-grid">{cards}</div>', unsafe_allow_html=True)