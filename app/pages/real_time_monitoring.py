import streamlit as st
from config.init import init_page, init_session_state

from widgets import *
from utils.functions import load_json, load_files

from preprocessing.fft_rt import list_fft_files
from monitoring.main import get_noc_names, start_and_end_times

from datetime import datetime, timezone, timedelta

# --- Application start ---
init_page("Real-time monitoring")
init_session_state()
st.title("Real-time monitoring")
# ------------------------

tab1, tab2, tab3, tab4 = st.tabs(['Real time', 'On demand', 'NOC comparison', 'Configuration'])

# Read configuration file
config_path = "jobs/automated/config.json"
config = load_json(config_path)

# Read paths from configuration
data_path = config["data_path"]
features_path = config["features_path"]
nocs_path = config["nocs_path"]
noc_log_path = config["noc_log_path"]
anomaly_log_path = config["anomaly_log_path"]
stations = config["stations"]

nocs = get_noc_names(noc_log_path, stations)
update_freq = timedelta(minutes=st.session_state.config["update_frequency"])

starttime, endtime = start_and_end_times(datetime.now(), 
                                        update_frequency=st.session_state.config["update_frequency"],
                                        delay = st.session_state.config["delay"])

st.session_state.start_date = datetime.date(starttime)
st.session_state.start_time = datetime.time(starttime)
st.session_state.end_date = datetime.date(endtime)
st.session_state.end_time = datetime.time(endtime)

# Define fragments
@st.fragment(run_every=update_freq)
def real_time_visualization(noc, nocs_path):

    col = st.columns(3)
    with col[0]:
        st.markdown("Time range for graphs:", help="Select a duration to view data from that many hours and minutes ago until now.")
        plot_time = forms.select_time_rt("plot_time_selector")
    
    with col[1]:
        logscale_rt = st.checkbox("Log scale", value=False, key="logscale_monitoring_rt",
                                    help="Display Y-axis using a logarithmic scale.")

        n_consecutive_rt = st.number_input("Number of minimum consecutive windows over threshold", min_value=1, value=3,
                                    key = "consecutive_windows_monitoring_rt", 
                                    help="When the number of consecutive windows over the threshold is greater or equal than this number, " \
                                    "the corresponding windows will be colored red in the graph.")

    with col[2]:
        st.button("Refresh", type='primary', use_container_width=True)

    # Arrange graphs (2 per row)
    for i, noc in enumerate(nocs):
        if i % 2 == 0:
            col1, col2 = st.columns(2) 

            # Left column
            with col1:
                with st.spinner("Loading graph..."):
                    plots.plot_dq_rt(noc[0], time_range=plot_time, logscale=logscale_rt, n_consecutive=n_consecutive_rt, nocs_path = nocs_path)
                tables.noc_summary(noc[0], nocs_path)
        else:
            # Right column
            with col2:
                with st.spinner("Loading graph..."):
                    plots.plot_dq_rt(noc[0], time_range=plot_time, logscale=logscale_rt, n_consecutive=n_consecutive_rt, nocs_path = nocs_path)
                tables.noc_summary(noc[0], nocs_path)


@st.fragment
def on_demand_visualization(stations, noc_log_path):
    col = st.columns(2)

    with col[1]:
        # Select NOC
        st.markdown("Select a station and Normal Operation Conditions (NOC):")
        with st.form("on_demand_selector_monitoring"):
            _, noc_name = forms.select_noc("noc_selector_monitoring", stations=stations, noc_log_path=noc_log_path)

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
                
            submit = st.form_submit_button("Plot", type='primary', use_container_width=True)
            
    with col[0]:
        # Display D and Q statistics
        if submit:
            with st.spinner("Calculating..."):
                plots.plot_dq(noc_name, starttime.replace(tzinfo=timezone.utc), endtime.replace(tzinfo=timezone.utc),
                            logscale=logscale, n_consecutive=n_consecutive, nocs_path = nocs_path)
        
@st.fragment
def noc_comparison(stations, noc_log_path, nocs_path):
    col = st.columns(2)

    with col[0]:
        # Select NOCs to compare
        st.write("#### Select first NOC:")
        _, noc1 = forms.select_noc("noc_selector_comparison1", stations, noc_log_path)
        tables.noc_summary(noc1, nocs_path)
        st.write("#### Select second NOC:")
        _, noc2 = forms.select_noc("noc_selector_comparison2", stations, noc_log_path)
        tables.noc_summary(noc2, nocs_path)
        
        with st.form(key="pca_selector_comparison"):
            st.write("#### PCA parameters:")
            subcol = st.columns(2)
            with subcol[0]:
                preprocessing = forms.select_preprocessing("prep_selector_noc_comparison")
            with subcol[1]:
                n_components = st.number_input("Number of principal components", min_value=1, value='min')

            submit = st.form_submit_button("Plot oMEDA comparison", type='primary', use_container_width=True)

    with col[1]:
        if submit:
            # Plot oMEDA
            with st.spinner("Calculating oMEDA..."):
                plots.plot_noc_omeda(noc1, noc2, preprocessing=preprocessing, n_components=n_components, 
                                    nocs_path=nocs_path)

# ---------- Real-time Visualization tab ----------
with tab1:    
    real_time_visualization(nocs, nocs_path)

# ---------- On-demand Visualization tab ----------
with tab2:
    on_demand_visualization(stations, noc_log_path)

# --------------- NOC comparison (oMEDA) tab -----------------
with tab3:
    noc_comparison(stations, noc_log_path, nocs_path)

# ------- Configuration tab: Display JSON configuration file --------
with tab4:
    st.header("Monitoring configuration")
    st.json(config)

