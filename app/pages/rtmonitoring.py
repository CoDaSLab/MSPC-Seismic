import streamlit as st
from config.init import init_page, init_session_state
from config.interface import header_rtmonitoring

from widgets import *

from monitoring import NOC, main
from datetime import datetime, timezone, timedelta

# --- Application start ---
init_page("Real-time monitoring")
init_session_state()
st.title("Real-time monitoring")
header_rtmonitoring()
# ------------------------

st.subheader("Visualization")

# Configuration file
config = st.session_state.config

update_freq = timedelta(minutes=config["general"]["update_frequency"])

starttime, endtime = main.start_and_end_times(datetime.now(timezone.utc), 
                                        update_frequency=config["general"]["update_frequency"],
                                        delay = config["general"]["delay"])

nocs = main.get_noc_names(config["paths"]["noc_log"], config["data"]["stations"])
if "start_date" not in st.session_state:
    st.session_state.start_date = datetime.date(starttime)
    st.session_state.start_time = datetime.time(starttime)
    st.session_state.end_date = datetime.date(endtime)
    st.session_state.end_time = datetime.time(endtime)

# Define fragments
@st.fragment(run_every=update_freq)
def real_time_visualization(config):

    with st.form("selector_monitoring_rt"):
        col = st.columns(3)
        with col[0]:
            st.markdown("Time range for graphs:", help="Select a duration to view data from that many hours and minutes ago until now.")
            plot_time = forms.select_time_rt("plot_time_selector")
        
        with col[1]:
            n_consecutive_rt = st.number_input("Number of minimum consecutive windows over threshold", min_value=1, value=3,
                                        key = "consecutive_windows_monitoring_rt", 
                                        help="When the number of consecutive windows over the threshold is greater or equal than this number, " \
                                        "the corresponding windows will be colored red in the graph.")
            logscale_rt = st.checkbox("Log scale", value=False, key="logscale_monitoring_rt",
                                        help="Display Y-axis using a logarithmic scale.")

        with col[2]:
            st.form_submit_button("Refresh", type='primary', use_container_width=True)

    # Arrange graphs (2 per row)
    for i, noc in enumerate(nocs):
        if i % 2 == 0:
            col1, col2 = st.columns(2) 

            # Left column
            with col1:
                with st.spinner("Loading graph..."):
                    plots.plot_dq_rt(noc[0], time_range=plot_time, logscale=logscale_rt, n_consecutive=n_consecutive_rt, 
                                     nocs_path = config["paths"]["nocs"])
                tables.noc_summary(noc[0], config["paths"]["nocs"])
        else:
            # Right column
            with col2:
                with st.spinner("Loading graph..."):
                    plots.plot_dq_rt(noc[0], time_range=plot_time, logscale=logscale_rt, n_consecutive=n_consecutive_rt, 
                                     nocs_path = config["paths"]["nocs"])
                tables.noc_summary(noc[0], config["paths"]["nocs"])
        

# ---------- Real-time Visualization ----------
real_time_visualization(config)
