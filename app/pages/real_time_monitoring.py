import streamlit as st
from config.init import init_page, init_session_state

from widgets import *
from utils.functions import load_data

from preprocessing.fft_rt import calculate_fft_rt, list_fft_files
from monitoring import NOC, main, mspc_rt

import numpy as np
import os
from datetime import datetime, timezone, timedelta
import pandas as pd

# --- Application start ---
init_page("Real-time monitoring")
init_session_state()
st.title("Real-time monitoring")
# ------------------------

tab = st.tabs(['Real time', 'On demand', 'NOC comparison', 'Configuration'])

# Configuration file
config = st.session_state.config

update_freq = timedelta(minutes=config["update_frequency"])

starttime, endtime = main.start_and_end_times(datetime.now(timezone.utc), 
                                        update_frequency=config["update_frequency"],
                                        delay = config["delay"])

nocs = main.get_noc_names(config["noc_log_path"], config["stations"])
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
                                     nocs_path = config["nocs_path"])
                tables.noc_summary(noc[0], config["nocs_path"])
        else:
            # Right column
            with col2:
                with st.spinner("Loading graph..."):
                    plots.plot_dq_rt(noc[0], time_range=plot_time, logscale=logscale_rt, n_consecutive=n_consecutive_rt, 
                                     nocs_path = config["nocs_path"])
                tables.noc_summary(noc[0], config["nocs_path"])


@st.fragment
def on_demand_visualization(config):
    col = st.columns(2)

    with col[1]:
        st.write("##### Select a station and Normal Operation Conditions (NOC):")
        # Select NOC
        station, noc_name = forms.select_noc("noc_selector_monitoring", stations=config["stations"], noc_log_path=config["noc_log_path"])

        # Display NOC details
        tables.noc_summary(noc_name, config["nocs_path"])

        with st.form("on_demand_selector_monitoring"):
            st.write("##### Select time range to plot:")
            # Select test time range
            starttime, endtime = forms.select_time("time_selector_monitoring")
            
            subcol = st.columns(2)
            with subcol[0]:
                calculate = st.checkbox("Run calculations", value=False,
                                help="Calculates features and statistics using parameters from monitoring configuration. " \
                                "If a previous calculation already exists, you can click on 'Plot' to plot the results directly.")
                
                logscale = st.checkbox("Log scale", value=False, key="logscale_monitoring",
                                    help="Display Y-axis using a logarithmic scale.")
            with subcol[1]:
                n_consecutive = st.number_input("Number of minimum consecutive windows over threshold", min_value=1, value=3,
                                        key = "consecutive_windows_monitoring", 
                                        help="When the number of consecutive windows over the threshold is greater or equal than this number, " \
                                        "the corresponding windows will be colored red in the graph.")
                
            submit = st.form_submit_button("Plot", type = "primary", use_container_width=True,
                                           help="Plot D and Q statistics. If no previous calculations exist, check the 'Run calculations' box and try again.")

    with col[0]:
        # Calculate and display D and Q statistics
        if submit:
            if starttime >= endtime:
                st.error("Start time cannot be after end time")
            else:
                if calculate:
                    with st.spinner("Calculating features..."):
                        features = calculate_fft_rt(starttime, endtime, network=config["network"], station=station, 
                                                    channels=config["channels"], window_size=config["window_size"],
                                                    window_shift=config["window_shift"], detrend=config["detrend"],
                                                    windowing=config["windowing"], fft_points=config["fft_points"], 
                                                    merge_method=config["merge_method"], merge_fill_value=config["merge_fill_value"],
                                                    pad_fill_value=config["pad_fill_value"], data_path=config["data_path"], 
                                                    cpus=config["cpus"], verbose=False, save=False)

                    with st.spinner("Perfoming MSPC..."):
                        noc = NOC.NOC.load(os.path.join(config["nocs_path"], noc_name))
                        test = np.hstack([features[key] for key in config["feature_types"]])
                        mspc_rt.mspc([noc], test, starttime, endtime, window_size=config["window_size"],
                                    window_shift=config["window_shift"], missing_rates=features["missing_rates"],
                                    plot=False, update_log=False, nocs_path=config["nocs_path"], verbose=False)

                with st.spinner("Plotting results..."):
                    plots.plot_dq(noc_name, starttime.replace(tzinfo=timezone.utc), endtime.replace(tzinfo=timezone.utc),
                                logscale=logscale, n_consecutive=n_consecutive, nocs_path = config["nocs_path"])
        
@st.fragment
def noc_comparison(config):
    col1 = st.columns(2)

    with col1[0]:
        # Select NOCs to compare
        st.write("##### Select first NOC:")
        _, noc1 = forms.select_noc("noc_selector_comparison1", config["stations"], config["noc_log_path"])
        tables.noc_summary(noc1, config["nocs_path"])
        st.write("##### Select second NOC:")
        _, noc2 = forms.select_noc("noc_selector_comparison2", config["stations"], config["noc_log_path"])
        tables.noc_summary(noc2, config["nocs_path"])
        
        with st.form(key="pca_selector_comparison"):
            st.write("##### PCA parameters:")
            subcol = st.columns(2)
            with subcol[0]:
                preprocessing = forms.select_preprocessing("prep_selector_noc_comparison")
            with subcol[1]:
                n_components = st.number_input("Number of principal components", min_value=1, value='min')

            submit = st.form_submit_button("Plot oMEDA comparison", type='primary', use_container_width=True)
        
        with st.form("dq_noc_selector_comparison"):
            st.write("##### Plot D and Q statistics for both NOCs:")
            col2 = st.columns(2)
            with col2[0]:
                logscale = st.checkbox("Log scale", value=False, key="logscale_noc_dq_monitoring",
                                                help="Display Y-axis using a logarithmic scale.")
            with col2[1]:
                submit_dq = st.form_submit_button("Plot D and Q statistics", use_container_width=True)

    with col1[1]:
        if submit:
            # Plot oMEDA
            with st.spinner("Calculating oMEDA..."):
                plots.plot_noc_omeda(noc1, noc2, preprocessing=preprocessing, n_components=n_components, 
                                    nocs_path=config["nocs_path"])
    
    if submit_dq:
        col3 = st.columns(2)
        with col3[0]:
            with st.spinner("Plotting results..."):
                plots.plot_dq_noc(noc1, nocs_path=config["nocs_path"], logscale=logscale)
        
        with col3[1]:
            with st.spinner("Plotting results.."):
                plots.plot_dq_noc(noc2, nocs_path=config["nocs_path"], logscale=logscale)


# ---------- Real-time Visualization tab ----------
with tab[0]:    
    real_time_visualization(config)

# ---------- On-demand Visualization tab ----------
with tab[1]:
    on_demand_visualization(config)

# --------------- NOC comparison (oMEDA) tab -----------------
with tab[2]:
    noc_comparison(config)

# ------- Configuration tab: Display JSON configuration file --------
with tab[3]:
    st.header("Monitoring configuration")
    st.json(config)

