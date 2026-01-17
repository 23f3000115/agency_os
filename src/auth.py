import streamlit as st
from supabase import create_client

# REMOVED: from src.services.supabase_client import supabase
# We do not want a global variable anymore.

def init_session():
    """
    Initialize session state variables AND a unique Supabase client
    for this specific user session.
    """
    # 1. Create a Unique Supabase Client for this Session
    if "supabase" not in st.session_state:
        try:
            # Load credentials from secrets.toml
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
            
            # create_client() is now called INSIDE the session check
            # This ensures every browser tab gets its own isolated connection
            st.session_state.supabase = create_client(url, key)
        except Exception as e:
            st.error(f"❌ critical: Database connection failed. {e}")
            st.stop()

    # 2. Initialize User State Placeholders
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'user_name' not in st.session_state:
        st.session_state.user_name = ""

def login_user(email, password):
    """Attempt to log in using the session-specific client."""
    
    # Grab the isolated client we created in init_session
    db = st.session_state.supabase

    try:
        # 1. Authenticate
        response = db.auth.sign_in_with_password({"email": email, "password": password})
        user = response.user
        
        # 2. Fetch Profile Role
        # Using 'db' ensures we use the TOKEN of the user we just logged in
        data = db.table("profiles").select("role, full_name").eq("id", user.id).execute()
        
        if data.data:
            st.session_state.user = user
            st.session_state.role = data.data[0]['role']
            st.session_state.user_name = data.data[0]['full_name']
            st.rerun() 
        else:
            st.error("User profile not found. Contact Admin.")
            
    except Exception as e:
        st.error(f"Login failed: {e}")

def logout_user():
    # Sign out using the session client
    if "supabase" in st.session_state:
        st.session_state.supabase.auth.sign_out()
    
    st.session_state.user = None
    st.session_state.role = None
    st.session_state.user_name = ""
    st.rerun()