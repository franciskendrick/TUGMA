import streamlit as st

# Page Config (browser title, favicon, and wide layout)
st.set_page_config(
    page_title="User Onboarding Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Injection (glassmorphism & subtle styling tweaks)
st.markdown("""
    <style>
    /* Dark subtle background refinement */
    .stApp {
        background-color: #0e1117;
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
    user_role = st.selectbox("Select Role", ["Data Analyst", "Data Scientist", "Engineer", "Guest"])
    theme_mode = st.toggle("Enable Advanced Mode", value=True)
    st.divider()
    st.caption("Version 1.0.0 | Built with Streamlit")

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