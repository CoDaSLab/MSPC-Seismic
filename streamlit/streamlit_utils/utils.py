
def init_session_state():
    import streamlit as st
    if 'sensor' not in st.session_state: st.session_state.sensor = 'PPMA'
    if 'channel' not in st.session_state: st.session_state.channel = 'HHE'
    from datetime import datetime, time
    if 'start_date' not in st.session_state: st.session_state.start_date = datetime(2021, 9, 19)
    if 'start_time' not in st.session_state: st.session_state.start_time = time(0,0,0)
    if 'end_date' not in st.session_state: st.session_state.end_date = datetime(2021, 9, 20)
    if 'end_time' not in st.session_state: st.session_state.end_time = time(0,0,0)
