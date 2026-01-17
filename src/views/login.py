import streamlit as st
from src.auth import login_user

def render_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("Agency OS 🔒")
        st.markdown("### Secure Workspace")
        
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Enter Workspace")
            
            if submitted:
                login_user(email, password)