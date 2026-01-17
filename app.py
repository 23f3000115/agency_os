import streamlit as st
from src.auth import init_session
from src.views.login import render_login
from src.views.owner_dashboard import render_owner_dashboard
from src.views.emp_dashboard import render_emp_dashboard

# --- 1. PAGE CONFIG ---
st.set_page_config(
    page_title="Agency OS", 
    page_icon="🏢", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. LOAD CSS HELPER ---
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Load the CSS file
try:
    local_css("assets/style.css")
except FileNotFoundError:
    st.warning("⚠️ CSS file not found. UI might look basic.")

# --- 3. INITIALIZE SESSION ---
init_session()

# --- 4. ROUTER LOGIC ---
if not st.session_state.get("user"):
    render_login()
else:
    role = st.session_state.get("role")
    
    if role == 'owner':
        render_owner_dashboard()
    elif role == 'employee':
        render_emp_dashboard()
    else:
        st.error(f"Unknown Role: {role}")
        if st.button("Reset Session"):
            st.session_state.clear()
            st.rerun()