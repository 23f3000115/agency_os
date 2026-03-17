import streamlit as st
from src.auth import logout_user
from src.views.chat_component import render_chat_widget

def render_manager_dashboard():
    # --- 1. SIDEBAR CONFIG ---
    st.sidebar.title(f"Manager: {st.session_state.get('user_name', 'Staff')}")
    
    # Currently, only one feature is active. 
    # You can easily add "Task Manager" or "Attendance" to this list later.
    menu = st.sidebar.radio("Command Post", ["Team Intercom"])
    
    if st.sidebar.button("Logout"):
        logout_user()

    # --- 2. TEAM INTERCOM (The Main View) ---
    if menu == "Team Intercom":
       # st.header("📡 Team Communication")
        # st.caption("Direct secure channel to all Employees and Agency HQ.")
        
        # This widget handles all the DB logic, finding users, and sending messages.
        render_chat_widget()