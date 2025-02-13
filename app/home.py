import streamlit as st
from config.init import init_page
from utils.utils import init_session_state

# --- Application start ---
init_page("Digivolcan Home")
init_session_state()

st.markdown("---")
st.markdown("<h1 style='text-align: center;'>Digivolcan Home</h1>", unsafe_allow_html=True)
