import streamlit as st
from config.init import init_page, init_session_state

from widgets import *
from utils import *

# --- Application start ---
init_page("Template")
init_session_state()
st.title("Template")
# ------------------------

# Code for page goes here:
# ...