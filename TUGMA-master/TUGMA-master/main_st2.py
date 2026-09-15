import streamlit as st

def load_css(file_name):
    with open(file_name, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.set_page_config(page_title="High-Contrast Theme", layout="wide")

# Load external CSS
load_css("style.css")

st.title("Terminal Dashboard")

col1, col2 = st.columns(2)

with col1:
    st.subheader("System Input")
    name = st.text_input("Operator Designation")
    st.button("Execute Initialization", type="primary")

with col2:
    st.subheader("Telemetry Readout")
    st.metric(label="Core Frequency", value="4.2 GHz", delta="Nominal")