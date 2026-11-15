# Login and registration screens.

import streamlit as st

from services.auth_service import AuthError, login, register
from src.database import Database


def render_auth(db_path):
    st.title("TUGMA")
    st.caption("Peer tutoring matchmaker")

    login_tab, register_tab = st.tabs(["Log in", "Create account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in")

        if submitted:
            user = None
            db = Database(db_path)
            try:
                user = login(db, email, password)
            except AuthError as error:
                st.error(str(error))
            finally:
                db.close()

            if user:
                st.session_state["user"] = user
                st.rerun()

    with register_tab:
        with st.form("register_form"):
            name = st.text_input("Full name")
            reg_email = st.text_input("Email", key="reg_email")
            account_type = st.radio("I am a", ["Student", "Tutor"], horizontal=True)
            c1, c2 = st.columns(2)
            year = c1.number_input("Year level", 1, 6, 1)
            course = c2.text_input("Course", "BCS")
            pw = st.text_input("Password", type="password", key="reg_pw")
            confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create account")

        st.caption(
            "Tutors appear in matching only after an administrator verifies them."
        )

        if submitted:
            user = None
            db = Database(db_path)
            try:
                user = register(
                    db, name, reg_email, pw, confirm,
                    account_type.lower(), int(year), course,
                )
            except AuthError as error:
                st.error(str(error))
            finally:
                db.close()

            if user:
                st.session_state["user"] = user
                st.rerun()
