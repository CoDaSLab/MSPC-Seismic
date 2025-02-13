import streamlit as st
from streamlit_utils.interface import header, logo
from streamlit_utils.utils import init_session_state

# --- Application start ---
st.set_page_config(
    page_title= "Digivolcan Home",
    layout='wide',
    page_icon="🌋",
    )

init_session_state()
logo()
header()

st.markdown("---")
st.markdown("<h1 style='text-align: center;'>Digivolcan Home</h1>", unsafe_allow_html=True)
