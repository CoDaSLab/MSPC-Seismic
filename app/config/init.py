import streamlit as st
from config.interface import header, logo

def init_app():
    if "app_start" not in st.session_state:
        st.session_state.app_start = False

    if st.session_state.app_start: return

    print("Initializing application ...")
    print("Adding directoried to sys.path ...")
    import os, sys
    path = os.getcwd()
    sys.path.insert(0, path)
    sys.path.insert(0, f"{path}/preprocessing/functions")

    st.session_state.app_start = True
    print("Application initialized correctly")
    return

def init_page(title = None, icon="🌋", layout="wide", sidebar="collapsed"):
    init_app()
    st.set_page_config(title, icon, layout, sidebar)
    # Hide sidebar expander
    st.markdown(
    """
    <style>
        [data-testid="collapsedControl"] {
            display: none
        }
    </style>
    """,
        unsafe_allow_html=True,
    )
    logo()
    header()
    return

