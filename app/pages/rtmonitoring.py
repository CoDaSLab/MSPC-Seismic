import streamlit as st
from config.init import init_page, init_session_state
from config.interface import header_rtmonitoring

from widgets import *

from monitoring import utils
from datetime import datetime, timezone, timedelta
import pickle
import time

# --- Application start ---
init_page("Real-time monitoring")
init_session_state()
st.title("Real-time monitoring")
header_rtmonitoring()
# ------------------------

st.subheader("Visualization")

# Configuration file
config = st.session_state.config

update_freq = timedelta(minutes=config["monitoring"]["update_frequency"])

starttime, endtime = utils.start_and_end_times(datetime.now(timezone.utc), 
                                        update_frequency=config["monitoring"]["update_frequency"],
                                        delay = config["monitoring"]["delay"])

if "start_date" not in st.session_state:
    st.session_state.start_date = datetime.date(starttime)
    st.session_state.start_time = datetime.time(starttime)
    st.session_state.end_date = datetime.date(endtime)
    st.session_state.end_time = datetime.time(endtime)

# Define fragments
@st.fragment(run_every=update_freq)
def real_time_visualization(config, nocs, key):
    with st.form(key):
        col = st.columns(3)
        with col[0]:
            st.markdown("Time range for graphs:", help="Select a duration to view data from that many hours and minutes ago until now.")
            plot_time = forms.select_time_rt("plot_time_selector")
        
        with col[1]:
            n_consecutive_rt = st.number_input("Number of minimum consecutive windows over threshold", min_value=1, value=3,
                                        key = key + "consecutive_windows", 
                                        help="When the number of consecutive windows over the threshold is greater or equal than this number, " \
                                        "the corresponding windows will be colored red in the graph.")
            logscale_rt = st.checkbox("Log scale", value=False, key=key + "logscale",
                                        help="Display Y-axis using a logarithmic scale.")

        with col[2]:
            weight_rt = st.slider("T-score weight", 0.0, 1.0, step=0.05)
            st.form_submit_button("Refresh", type='primary', use_container_width=True)

    # Arrange graphs (2 per row)
    for i, noc in enumerate(nocs):
        if i % 2 == 0:
            col1, col2 = st.columns(2) 

            # Left column
            with col1:
                with st.spinner("Loading graph..."):
                    graph_attempt = 0
                    while graph_attempt < 3:
                        try:
                            plots.plot_tscore_rt(noc[0], time_range=plot_time, T_weight=weight_rt, logscale=logscale_rt, 
                                n_consecutive=n_consecutive_rt, nocs_path=config["paths"]["nocs"])
                            tables.noc_summary(noc[0], config["paths"]["nocs"])
                            break
                        except pickle.UnpicklingError:
                            time.sleep(5)
                            graph_attempt += 1
                    else:
                        st.error(f"Failed to load graph for NOC {noc[0]}.")
        else:
            # Right column
            with col2:
                with st.spinner("Loading graph..."):
                    graph_attempt = 0
                    while graph_attempt < 3:
                        try:
                            plots.plot_tscore_rt(noc[0], time_range=plot_time, T_weight=weight_rt, logscale=logscale_rt, 
                                n_consecutive=n_consecutive_rt, nocs_path=config["paths"]["nocs"])
                            tables.noc_summary(noc[0], config["paths"]["nocs"])
                            break
                        except pickle.UnpicklingError:
                            time.sleep(5)
                            graph_attempt += 1
                    else:
                        st.error(f"Failed to load graph for NOC {noc[0]}.")
        

# ---------- Real-time Visualization ----------
try:
    avail_stations = utils.get_available_stations(config["paths"]["latest_pulls_log"], tolerance=2 * config["monitoring"]["update_frequency"])
except FileNotFoundError as e:
    st.error(f"Latest data downloads log not available. More details:\n{e}")
try:
    nocs = utils.get_noc_names(config["paths"]["noc_log"], avail_stations)
    real_time_visualization(config, nocs=nocs, key="monitoring_rt")
except FileNotFoundError as e:
    st.error(f"NOC list not available. More details:\n{e}")