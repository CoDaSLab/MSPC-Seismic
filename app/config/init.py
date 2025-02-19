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


def init_session_state():
    import streamlit as st
    if 'sensor' not in st.session_state: st.session_state.sensor = 'PPMA'
    if 'channel' not in st.session_state: st.session_state.channel = 'HHE'
    from datetime import datetime, time
    if 'start_date' not in st.session_state: st.session_state.start_date = datetime(2021, 9, 19)
    if 'start_time' not in st.session_state: st.session_state.start_time = time(0,0,0)
    if 'end_date' not in st.session_state: st.session_state.end_date = datetime(2021, 9, 20)
    if 'end_time' not in st.session_state: st.session_state.end_time = time(0,0,0)
