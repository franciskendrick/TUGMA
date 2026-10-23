import pickle
import re
import uuid
from datetime import datetime
from pathlib import Path
 
import bcrypt
import streamlit as st
import streamlit_authenticator as stauth
 
BASE_DIR = Path(__file__).parent
USERS_FILE = BASE_DIR / "users.pkl"          # accounts (login + profile)
BOOKINGS_FILE = BASE_DIR / "bookings.pkl"    # student -> tutor session requests
 
SUBJECTS = [
    "Mathematics", "Science", "English", "Filipino", "Programming",
    "Physics", "Chemistry", "Biology", "Economics", "Accounting",
]
 
st.set_page_config(
    page_title="TUGMA",
    page_icon="❇️",
    layout="wide",
    initial_sidebar_state="expanded",
)
 
 
# --------------------------------------------------------------------------
# Styling
# --------------------------------------------------------------------------
def load_css(file_name: str) -> None:
    css_path = BASE_DIR / file_name
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>",
                    unsafe_allow_html=True)
    else:
        st.warning(f"{file_name} not found, using default look.")
 
 
load_css("style.css")
 
 
def hero(title, subtitle, badge=None):
    """Green banner with white text. Only pass trusted/static strings here."""
    badge_html = f'<span class="role-badge">{badge}</span>' if badge else ""
    st.markdown(
        f'<div class="tugma-hero"><h1>{title}</h1><p>{subtitle}</p>{badge_html}</div>',
        unsafe_allow_html=True,
    )
 
 
# --------------------------------------------------------------------------
# "Database" helpers (pickle files)
# --------------------------------------------------------------------------
def hash_pw(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
 
 
def load_users() -> dict:
    """Load accounts; create the file with two demo accounts on first run."""
    if not USERS_FILE.exists():
        users = {
            "usernames": {
                "student1": {
                    "name": "Peter Parker", "password": hash_pw("student123"),
                    "role": "Student", "course": "BS Computer Science", "bio": "",
                },
                "tutor1": {
                    "name": "Tony Stark", "password": hash_pw("tutor123"),
                    "role": "Tutor", "subjects": ["Programming", "Physics"],
                    "bio": "Engineer and part-time tutor. Happy to help!",
                },
            }
        }
        save_users(users)
        return users
    try:
        with USERS_FILE.open("rb") as f:
            return pickle.load(f)
    except (EOFError, pickle.UnpicklingError):
        st.error("users.pkl is empty or corrupted. Delete it and reload to reset.")
        st.stop()
 
 
def save_users(users: dict) -> None:
    with USERS_FILE.open("wb") as f:
        pickle.dump(users, f)
 
 
def load_bookings() -> list:
    if not BOOKINGS_FILE.exists():
        return []
    try:
        with BOOKINGS_FILE.open("rb") as f:
            return pickle.load(f)
    except (EOFError, pickle.UnpicklingError):
        return []
 
 
def save_bookings(bookings: list) -> None:
    with BOOKINGS_FILE.open("wb") as f:
        pickle.dump(bookings, f)
 
 
# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------
users_db = load_users()
 
authenticator = stauth.Authenticate(
    credentials=users_db,
    cookie_name="tugma_cookie",
    key="tugma_auth_key",
    cookie_expiry_days=15,
)
 
 
def pill(status: str) -> str:
    return f'<span class="pill pill-{status}">{status.capitalize()}</span>'
 
 
def signup_form() -> None:
    st.subheader("Create your account")
    role = st.radio("I want to join as a…", ["Student", "Tutor"], horizontal=True,
                    key="signup_role")
    with st.form("signup_form", clear_on_submit=False):
        full_name = st.text_input("Full name")
        new_username = st.text_input("Username", help="Letters, numbers, underscore. Min 3.")
        c1, c2 = st.columns(2)
        pw = c1.text_input("Password", type="password", help="At least 6 characters")
        pw2 = c2.text_input("Confirm password", type="password")
 
        subjects, extra = [], ""
        if role == "Tutor":
            subjects = st.multiselect("Subjects you teach", SUBJECTS)
            extra = st.text_area("Short bio", height=80,
                                 placeholder="Tell students about your experience...")
        else:
            extra = st.text_input("Course / grade level (optional)")
 
        submitted = st.form_submit_button("Sign up", type="primary",
                                          use_container_width=True)
 
    if not submitted:
        return
 
    uname = new_username.strip().lower()
    if not full_name.strip() or not uname or not pw:
        st.error("Please fill in your name, username and password.")
    elif not re.fullmatch(r"[a-z0-9_]{3,}", uname):
        st.error("Username must be 3+ characters: letters, numbers or underscore.")
    elif len(pw) < 6:
        st.error("Password must be at least 6 characters.")
    elif pw != pw2:
        st.error("Passwords do not match.")
    elif uname in users_db["usernames"]:
        st.error("That username is taken. Please choose another.")
    elif role == "Tutor" and not subjects:
        st.error("Please pick at least one subject you teach.")
    else:
        record = {"name": full_name.strip(), "password": hash_pw(pw), "role": role}
        if role == "Tutor":
            record.update({"subjects": subjects, "bio": extra.strip()})
        else:
            record.update({"course": extra.strip(), "bio": ""})
        users_db["usernames"][uname] = record
        save_users(users_db)
        st.success("Account created! Open the **Log in** tab and sign in.")
 
 
# --------------------------------------------------------------------------
# Student UI
# --------------------------------------------------------------------------
def student_view(username: str) -> None:
    me = users_db["usernames"][username]
    bookings = load_bookings()
    mine = [b for b in bookings if b["student"] == username]
 
    hero(f"Hello, {me['name'].split()[0]}!", "Find a tutor and book your next session.",
         badge="Student")
 
    m1, m2, m3 = st.columns(3)
    m1.metric("Requests sent", len(mine))
    m2.metric("Accepted", sum(b["status"] == "accepted" for b in mine))
    m3.metric("Pending", sum(b["status"] == "pending" for b in mine))
    st.write("")
 
    tab_find, tab_req, tab_prof = st.tabs(["🔎 Find a Tutor", "📅 My Requests", "👤 My Profile"])
 
    with tab_find:
        tutors = {u: d for u, d in users_db["usernames"].items() if d["role"] == "Tutor"}
        f1, f2 = st.columns([1, 2])
        subject_filter = f1.selectbox("Subject", ["All"] + SUBJECTS)
        search = f2.text_input("Search tutor by name", placeholder="e.g., Tony")
 
        shown = 0
        for t_user, t in tutors.items():
            if subject_filter != "All" and subject_filter not in t.get("subjects", []):
                continue
            if search and search.lower() not in t["name"].lower():
                continue
            shown += 1
            with st.container(border=True):
                st.subheader(t["name"])
                st.caption("Teaches: " + ", ".join(t.get("subjects", [])))
                if t.get("bio"):
                    st.write(t["bio"])
                with st.expander("Request a session"):
                    with st.form(f"req_{t_user}", clear_on_submit=True):
                        subj = st.selectbox("Subject", t.get("subjects", SUBJECTS))
                        when = st.text_input("Preferred day/time",
                                             placeholder="e.g., Saturday 3 PM")
                        msg = st.text_area("Message (optional)", height=70)
                        if st.form_submit_button("Send request", type="primary"):
                            if not when.strip():
                                st.error("Please enter a preferred day/time.")
                            else:
                                bookings.append({
                                    "id": uuid.uuid4().hex, "student": username,
                                    "tutor": t_user, "subject": subj,
                                    "when": when.strip(), "message": msg.strip(),
                                    "status": "pending",
                                    "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                })
                                save_bookings(bookings)
                                st.success("Request sent!")
                                st.rerun()
        if shown == 0:
            st.info("No tutors match your search yet.")
 
    with tab_req:
        if not mine:
            st.info("You haven't requested any sessions yet. Head to **Find a Tutor**.")
        for b in reversed(mine):
            tutor_name = users_db["usernames"].get(b["tutor"], {}).get("name", b["tutor"])
            with st.container(border=True):
                st.markdown(f"**{b['subject']}** with **{tutor_name}** &nbsp; {pill(b['status'])}",
                            unsafe_allow_html=True)
                st.caption(f"Preferred: {b['when']}  •  Sent {b['created']}")
                if b["message"]:
                    st.write(b["message"])
                if b["status"] == "pending" and st.button("Cancel request", key=f"c_{b['id']}"):
                    save_bookings([x for x in bookings if x["id"] != b["id"]])
                    st.rerun()
 
    with tab_prof:
        with st.form("student_profile"):
            name = st.text_input("Full name", value=me["name"])
            course = st.text_input("Course / grade level", value=me.get("course", ""))
            if st.form_submit_button("Save profile", type="primary"):
                if name.strip():
                    me["name"], me["course"] = name.strip(), course.strip()
                    save_users(users_db)
                    st.success("Profile updated.")
                else:
                    st.error("Name cannot be empty.")
 
 
# --------------------------------------------------------------------------
# Tutor UI
# --------------------------------------------------------------------------
def tutor_view(username: str) -> None:
    me = users_db["usernames"][username]
    bookings = load_bookings()
    mine = [b for b in bookings if b["tutor"] == username]
    pending = [b for b in mine if b["status"] == "pending"]
    accepted = [b for b in mine if b["status"] == "accepted"]
 
    hero(f"Welcome, {me['name'].split()[0]}!", "Manage your requests and sessions.",
         badge="Tutor")
 
    m1, m2, m3 = st.columns(3)
    m1.metric("New requests", len(pending))
    m2.metric("Upcoming sessions", len(accepted))
    m3.metric("Students helped", len({b["student"] for b in accepted}))
    st.write("")
 
    tab_req, tab_sched, tab_prof = st.tabs(
        [f"📥 Requests ({len(pending)})", "🗓️ My Sessions", "👤 My Profile"])
 
    def student_name(u: str) -> str:
        return users_db["usernames"].get(u, {}).get("name", u)
 
    with tab_req:
        if not pending:
            st.info("No pending requests right now.")
        for b in pending:
            with st.container(border=True):
                st.markdown(f"**{student_name(b['student'])}** wants help with **{b['subject']}**")
                st.caption(f"Preferred: {b['when']}  •  Sent {b['created']}")
                if b["message"]:
                    st.write(b["message"])
                c1, c2, _ = st.columns([1, 1, 3])
                if c1.button("Accept", key=f"a_{b['id']}", type="primary"):
                    b["status"] = "accepted"
                    save_bookings(bookings)
                    st.rerun()
                if c2.button("Decline", key=f"d_{b['id']}"):
                    b["status"] = "declined"
                    save_bookings(bookings)
                    st.rerun()
 
    with tab_sched:
        if not accepted:
            st.info("Accepted sessions will appear here.")
        for b in accepted:
            with st.container(border=True):
                st.markdown(f"**{b['subject']}** with **{student_name(b['student'])}** "
                            f"&nbsp; {pill('accepted')}", unsafe_allow_html=True)
                st.caption(f"When: {b['when']}")
 
    with tab_prof:
        with st.form("tutor_profile"):
            name = st.text_input("Full name", value=me["name"])
            subjects = st.multiselect("Subjects you teach", SUBJECTS,
                                      default=me.get("subjects", []))
            bio = st.text_area("Short bio", value=me.get("bio", ""), height=100)
            if st.form_submit_button("Save profile", type="primary"):
                if not name.strip() or not subjects:
                    st.error("Name and at least one subject are required.")
                else:
                    me.update({"name": name.strip(), "subjects": subjects, "bio": bio.strip()})
                    save_users(users_db)
                    st.success("Profile updated. Students will see these changes.")
 
 
# --------------------------------------------------------------------------
# Router: logged-out -> Log in / Sign up tabs, logged-in -> role dashboard
# --------------------------------------------------------------------------
status = st.session_state.get("authentication_status")
 
if not status:
    hero("TUGMA", "Match with the right tutor. Learn together.")
    left, mid, right = st.columns([1, 2, 1])
    with mid:
        tab_login, tab_signup = st.tabs(["🔐 Log in", "📝 Sign up"])
        with tab_login:
            try:
                authenticator.login(location="main")
            except Exception as e:
                st.error(e)
            if st.session_state.get("authentication_status") is False:
                st.error("Username or password is incorrect.")
            else:
                st.caption("Demo: student1 / student123  •  tutor1 / tutor123")
        with tab_signup:
            signup_form()
else:
    username = st.session_state["username"]
    me = users_db["usernames"].get(username)
    if me is None:  # account was removed while the cookie was still valid
        authenticator.logout("Logout", "sidebar")
        st.stop()
 
    with st.sidebar:
        st.markdown("### ❇️ TUGMA")
        st.write(f"**{me['name']}**")
        st.caption(f"@{username} • {me['role']}")
        st.divider()
        authenticator.logout("Logout", "sidebar")
 
    if me["role"] == "Tutor":
        tutor_view(username)
    else:
        student_view(username)
 
#Old Code (TRASH)
# from pathlib import Path
# import pickle
# import bcrypt
# import streamlit as st
# import streamlit_authenticator as stauth
#
# # 1. Page Config
# st.set_page_config(
#     page_title="TUGMA",
#     page_icon="❇️",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )
#
# # 2. Path to unified user database file
# db_file = Path(__file__).parent / "users.pkl"
#
# # Initialize default users if users.pkl doesn't exist yet
# if not db_file.exists():
#     default_credentials = {
#         "usernames": {
#             "student1": {
#                 "name": "Peter Parker",
#                 "password": bcrypt.hashpw(
#                     "student123".encode(), bcrypt.gensalt()
#                 ).decode(),
#                 "role": "Student",
#             },
#             "tutor1": {
#                 "name": "Tony Stark",
#                 "password": bcrypt.hashpw(
#                     "tutor123".encode(), bcrypt.gensalt()
#                 ).decode(),
#                 "role": "Tutor",
#             },
#         }
#     }
#     with open(db_file, "wb") as file:
#         pickle.dump(default_credentials, file)
#
# # Load existing user credentials
# with open(db_file, "rb") as file:
#     credentials = pickle.load(file)
#
# # 3. Instantiate Authenticator
# authenticator = stauth.Authenticate(
#     credentials=credentials,
#     cookie_name="tugma_cookie",
#     key="tugma_auth_key",
#     cookie_expiry_days=15,
# )
#
# # 4. Authentication / Registration Tabs UI
# if not st.session_state.get("authentication_status"):
#     tab_login, tab_signup = st.tabs(["🔐 Login", "📝 Sign Up"])
#
#     with tab_login:
#         try:
#             authenticator.login(location="main")
#         except Exception as e:
#             st.error(e)
#
#         authentication_status = st.session_state.get("authentication_status")
#         if authentication_status is False:
#             st.error("Username/Password is incorrect")
#         elif authentication_status is None:
#             st.info("Please enter your username and password to continue.")
#
#     with tab_signup:
#         st.subheader("Create New Account")
#         with st.form("signup_form"):
#             new_name = st.text_input("Full Name")
#             new_username = st.text_input("Username")
#             new_password = st.text_input("Password", type="password")
#             confirm_password = st.text_input(
#                 "Confirm Password", type="password"
#             )
#             new_role = st.selectbox("Role", ["Student", "Tutor"])
#
#             signup_submitted = st.form_submit_button("Register Account")
#
#             if signup_submitted:
#                 if not new_name or not new_username or not new_password:
#                     st.error("Please fill in all fields.")
#                 elif new_password != confirm_password:
#                     st.error("Passwords do not match.")
#                 elif new_username in credentials["usernames"]:
#                     st.error(
#                         "Username already exists! Choose a different one."
#                     )
#                 else:
#                     # Hash new password with bcrypt
#                     hashed_pwd = bcrypt.hashpw(
#                         new_password.encode(), bcrypt.gensalt()
#                     ).decode()
#
#                     # Save new user into memory and write to users.pkl
#                     credentials["usernames"][new_username] = {
#                         "name": new_name,
#                         "password": hashed_pwd,
#                         "role": new_role,
#                     }
#                     with open(db_file, "wb") as file:
#                         pickle.dump(credentials, file)
#
#                     st.success(
#                         "Account created successfully! Go to the Login tab to"
#                         " log in."
#                     )
#
# # 5. Main Dashboard View (Only accessible when logged in)
# else:
#     user_name = st.session_state.get("name")
#     username = st.session_state.get("username")
#     user_role = credentials["usernames"][username].get("role", "Student")
#
#     # CSS Styling
#     st.markdown(
#         """
#         <style>
#         .stApp {
#             background-color: #002D04;
#         }
#         div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] {
#             border-radius: 10px;
#         }
#         </style>
#     """,
#         unsafe_allow_html=True,
#     )
#
#     # Sidebar Header & Session Controls
#     with st.sidebar:
#         st.header("⚙️ Configuration")
#         st.write(f"Logged in as: **{user_name}** (`{username}`)")
#         st.write(f"Account Role: **{user_role}**")
#         st.divider()
#         authenticator.logout("Logout", "sidebar")
#
#     # Main Hero Header
#     st.title("User Portal")
#     st.caption("A modernized layout replacing standard sequential inputs.")
#     st.divider()
#
#     # Two-Column UI Layout
#     col1, col2 = st.columns([1, 1], gap="large")
#
#     with col1:
#         st.subheader("👤 Profile Setup")
#         with st.container(border=True):
#             profile_name = st.text_input("Full Name", value=user_name)
#             bio = st.text_area(
#                 "Short Bio",
#                 placeholder="Briefly describe your core focus...",
#                 height=100,
#             )
#             submit_btn = st.button(
#                 "Initialize Profile", use_container_width=True, type="primary"
#             )
#
#     with col2:
#         st.subheader("📊 Live Output Preview")
#         if submit_btn:
#             if profile_name:
#                 st.success(f"Welcome aboard, **{profile_name}**!")
#
#                 m1, m2 = st.columns(2)
#                 m1.metric(label="Assigned Role", value=user_role)
#                 m2.metric(label="Status", value="Active", delta="Verified")
#
#                 if bio:
#                     st.info(f"**Bio Overview:** {bio}")
#             else:
#                 st.error("Please enter your name before submitting.")
#         else:
#             st.info(
#                 "Fill out the profile setup on the left to render the dashboard"
#                 " metrics."
#             )