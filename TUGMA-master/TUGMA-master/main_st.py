import streamlit as st
import pickle
from pathlib import Path
import streamlit_authenticator as stauth
import bcrypt

# Page Config (browser title, favicon, and wide layout)
st.set_page_config(
    page_title="TUGMA",
    page_icon="❇️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load hashed passwords
file_path = Path(__file__).parent / "hashed.pw.pkl"

if file_path.exists():
    try:
        with file_path.open("rb") as file:
            hashed_passwords = pickle.load(file)
    except EOFError:
        st.error(
            "the hash file is empty"
        )
        st.stop()
else:
    st.error("file not found")
    st.stop()

credentials = {
    "usernames": {
        "student1" : {"name": "Peter Parker", "password:": hashed_passwords[0], "role": "Student"},
        "tutor1": {"name": "Tony Stark", "password:": hashed_passwords[1], "role": "Tutor"}
    }
}

authenticator = stauth.Authenticate(
    credentials=credentials,
    cookie_name="tugma_cookie",
    key="tugma_auth_key",
    cookie_expiry_days=15,
)
# authenticator = stauth.Authenticate (names, usernames, hashed_passwords, "sales_dashboard", "abcdef", cookie_expiry_days=15)
try:
    authenticator.login(location="main")
except Exception as e:
    st.error(e)

authentication_status = st.session_state.get("authentication_status")
user_name = st.session_state.get("name")
username = st.session_state.get("username")

# authentication process
if not authentication_status:
    st.error("Username/Password is incorrect")

elif not authentication_status:
    st.warning("Please enter username and password")

if authentication_status:
#CSS injection
    st.markdown("""
    <style>
    /* Dark subtle background refinement */
    .stApp {
        background-color: #002D04;
    }
    /* Card-like container styling */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] {
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar for Settings & Metadata
with st.sidebar:
    st.header("⚙️ Configuration")
    user_role = st.selectbox("Select Role", ["Tutor", "Student"])
    # theme_mode = st.toggle("Enable Advanced Mode", value=True)
    st.divider()

# Main Hero Header
st.title("User Portal")
st.caption("A modernized layout replacing standard sequential inputs.")
st.divider()

# Two-Column UI Layout
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("👤 Profile Setup")
    with st.container(border=True):
        name = st.text_input("Full Name", placeholder="e.g., Alex Mercer")
        bio = st.text_area("Short Bio", placeholder="Briefly describe your core focus...", height=100)

        submit_btn = st.button("Initialize Profile", use_container_width=True, type="primary")

with col2:
    st.subheader("📊 Live Output Preview")
    if submit_btn:
        if name:
            st.success(f"Welcome aboard, **{name}**!")

            # Interactive Stat Cards
            m1, m2 = st.columns(2)
            m1.metric(label="Assigned Role", value=user_role)
            m2.metric(label="Status", value="Active", delta="Verified")

            if bio:
                st.info(f"**Bio Overview:** {bio}")
        else:
            st.error("Please enter your name before submitting.")
    else:
        st.info("Fill out the profile setup on the left to render the dashboard metrics.")

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