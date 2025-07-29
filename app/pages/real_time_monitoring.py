import streamlit as st
from config.init import init_page, init_session_state

from widgets import *
from utils.functions import load_json, load_files

from preprocessing.fft_rt import list_fft_files
from monitoring.main import get_available_stations

# --- Application start ---
init_page("Real time monitoring")
init_session_state()
st.title("Real time monitoring")
# ------------------------

tab1, tab2 = st.tabs(['Visualization', 'Configuration'])

# Read configuration file
config_path = "monitoring/config.json"
config = load_json(config_path)

# Read paths from configuration
data_path = config["data_path"]
features_path = config["features_path"]
nocs_path = config["nocs_path"]
noc_log_path = config["noc_log_path"]
anomaly_log_path = config["anomaly_log_path"]
stations = config["stations"]


# ---------- Visualization tab: Display D and Q-statistics ----------
with tab1:
    col = st.columns(2)
    noc_names = load_files(filepath=noc_log_path)

    with col[1]:
        # Select NOC
        st.markdown("Select a station and Normal Operation Conditions (NOC):")
        station, noc_name = forms.select_noc("noc_selector_monitoring", stations=stations, noc_log_path=noc_log_path)

        # Display NOC details
        tables.noc_summary(noc_name, nocs_path)

        # Select test time range
        starttime, endtime = forms.select_time("time_selector_monitoring")

        subcol = st.columns(2)
        with subcol[0]:
            logscale = st.checkbox("Log scale", value=False, key="logscale_monitoring",
                                help="Display Y-axis using a logarithmic scale.")
        with subcol[1]:
            n_consecutive = st.number_input("Number of minimum consecutive windows over threshold", min_value=1, value=3,
                                       key = "consecutive_windows_monitoring", 
                                       help="When the number of consecutive windows over the threshold is greater or equal than this number, " \
                                       "the corresponding windows will be colored red in the graph.")
            

    with col[0]:
        plots.plot_dq(noc_name, starttime, endtime, logscale=logscale,)






# ------- Configuration tab: Display JSON configuration file --------
with tab2:
    st.header("Monitoring configuration")
    st.json(config)

