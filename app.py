import streamlit as st
from src.auth import init_session
from src.views.login import render_login
from src.views.owner_dashboard import render_owner_dashboard
from src.views.emp_dashboard import render_emp_dashboard
from src.views.manager_dashboard import render_manager_dashboard
import time
from ui.components import load_css

# --- 1. PAGE CONFIG (Must be the very first Streamlit command!) ---
st.set_page_config(
    page_title="Agency OS", 
    page_icon="🏢", 
    layout="wide",
    initial_sidebar_state="expanded"
)

load_css()

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
    try:
        # THE FIX: Changed "role" to "user_role" to match Postgres auth
        role = st.session_state.get("user_role")
        
        if role == 'owner':
            render_owner_dashboard()
        elif role == 'employee':
            render_emp_dashboard()
        elif role == 'manager':          
            render_manager_dashboard()
        else:
            st.error(f"Unknown Role: {role}")
            if st.button("Reset Session"):
                st.session_state.clear()
                st.rerun()
                
    except Exception as e:
        error_msg = str(e)
        
        # CHECK FOR "JWT EXPIRED" OR AUTH ERRORS (Left intact as requested)
        if "JWT expired" in error_msg or "PGRST303" in error_msg:
            st.warning("⚠️ Session expired. Please log in again.")
            time.sleep(2)
            # Clear Session and Restart
            st.session_state.clear()
            st.rerun()
        else:
            # If it's a real bug, show it
            st.error(f"An unexpected error occurred: {e}")