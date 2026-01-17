import streamlit as st
from supabase import create_client, Client

# Initialize once and cache it
@st.cache_resource
def get_supabase_client():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ Supabase Connection Error: {e}")
        return None

supabase = get_supabase_client()