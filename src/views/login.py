import streamlit as st
from src.auth import authenticate_user

def render_login():
    st.markdown("<h1 style='text-align: center; color: #c5a059;'>Agency OS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Secure Command Center</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        with st.container(border=True):
            st.subheader("System Login")
            
            with st.form("login_form"):
                email = st.text_input("Email Address")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Access Dashboard", use_container_width=True)
                
                if submit:
                    if not email or not password:
                        st.warning("Please enter both email and password.")
                    else:
                        with st.spinner("Authenticating..."):
                            # This MUST point to the new Postgres function
                            success = authenticate_user(email, password)
                            if success:
                                st.success("Access Granted.")
                                st.rerun() 
                            else:
                                st.error("Invalid credentials. Please try again.")