import streamlit as st


def load_css():
    with open("ui/styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def dashboard_card(title):

    st.markdown(f"""
    <div class="dashboard-card fade-in">
    <h4>{title}</h4>
    """, unsafe_allow_html=True)


def end_card():
    st.markdown("</div>", unsafe_allow_html=True)


def section_title(title):
    st.markdown(f"### {title}")