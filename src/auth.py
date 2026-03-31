import streamlit as st
import bcrypt
from sqlalchemy import text

def init_session():
    """Initializes default session state variables on first load."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'user_name' not in st.session_state:
        st.session_state.user_name = None

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def authenticate_user(email, password):
    """Verifies credentials against Postgres and sets up the session."""
    conn = st.connection("postgresql", type="sql")
    
    with conn.session as s:
        sql = "SELECT id, full_name, email, password_hash, role FROM users WHERE email = :email"
        user = s.execute(text(sql), {"email": email}).mappings().fetchone()
        
    if user and verify_password(password, user["password_hash"]):
        class SessionUser: 
            pass
        
        # SAFETY NET: If the database role is missing/NULL, force it to 'owner'
        fetched_role = user["role"]
        if not fetched_role:
            fetched_role = "owner"
            
        st.session_state.user = SessionUser()
        st.session_state.user.id = str(user["id"])
        st.session_state.user_name = user["full_name"]
        st.session_state.user_role = fetched_role
        st.session_state.authenticated = True
        return True
            
    return False

def logout_user():
    """Clears the session and sends the user back to login."""
    st.session_state.clear()
    st.rerun()
