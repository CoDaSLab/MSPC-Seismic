import streamlit as st
from config.init import init_page, init_session_state
from config.interface import header_monitoring

from widgets import *

from preprocessing.fft_rt import calculate_fft_rt
from monitoring import mspc_rt, utils

import numpy as np
import os
from datetime import datetime, timezone, timedelta

# --- Application start ---
init_page("Monitoring - Visualization")
init_session_state()
st.title("Monitoring")
header_monitoring()
# ------------------------

# On-demand
st.subheader("On-demand visualization")

config = st.session_state.config

starttime, endtime = utils.start_and_end_times(datetime.now(timezone.utc), 
                                            update_frequency=config["general"]["update_frequency"],
                                            delay = config["general"]["delay"])

nocs = utils.get_noc_names(config["paths"]["noc_log"], config["data"]["stations"])

if "start_date" not in st.session_state:
    st.session_state.start_date = datetime.date(starttime)
    st.session_state.start_time = datetime.time(starttime)
    st.session_state.end_date = datetime.date(endtime)
    st.session_state.end_time = datetime.time(endtime)


key = "on_demand"
col = st.columns(2)

with col[1]:
    st.write("##### Select a station and Normal Operation Conditions (NOC):")
    # Select NOC
    station, noc_name = forms.select_noc(key + "noc_selector", stations=config["data"]["stations"], noc_log_path=config["paths"]["noc_log"])

    # Display NOC details
    tables.noc_summary(noc_name, config["paths"]["nocs"])

    with st.form(key + "selector"):
        st.write("##### Select time range to plot:")
        # Select test time range
        starttime, endtime = forms.select_time(key)
        
        subcol = st.columns(2)
        with subcol[0]:
            calculate = st.checkbox("Run calculations", value=False,
                            help="Calculates features and statistics using parameters from monitoring configuration. " \
                            "If a previous calculation already exists, you can click on 'Plot' to plot the results directly.")
            
            logscale = st.checkbox("Log scale", value=False, key = key + "logscale",
                                help="Display Y-axis using a logarithmic scale.")
        with subcol[1]:
            n_consecutive = st.number_input("Number of minimum consecutive windows over threshold", min_value=1, value=3,
                                    key = key + "consecutive_windows", 
                                    help="When the number of consecutive windows over the threshold is greater or equal than this number, " \
                                    "the corresponding windows will be colored red in the graph.")
            weight = st.slider("T-score weight", 0.0, 1.0, step=0.05)
            
        submit = st.form_submit_button("Plot", type = "primary", use_container_width=True,
                                        help="Plot T-scores. If no previous calculations exist, check the 'Run calculations' box and try again.")

with col[0]:
    # Calculate and display D and Q statistics
    if submit:
        if starttime >= endtime:
            st.error("Start time cannot be after end time")
        else:
            if calculate:
                with st.spinner("Calculating features..."):
                    features = calculate_fft_rt(starttime, endtime, network=config["data"]["network"], station=station, 
                                                channels=config["data"]["channels"], window_size=config["features"]["window_size"],
                                                window_shift=config["features"]["window_shift"], detrend=config["features"]["detrend"],
                                                windowing=config["features"]["windowing"], fft_points=config["features"]["fft_points"], 
                                                merge_method=config["features"]["merge_method"], merge_fill_value=config["features"]["merge_fill_value"],
                                                pad_fill_value=config["features"]["pad_fill_value"], data_path=config["paths"]["data"], 
                                                cpus=config["features"]["cpus"], verbose=False, save=False)

                with st.spinner("Perfoming MSPC..."):
                    noc_path = os.path.join(config["paths"]["nocs"], noc_name)
                    test = np.hstack([features[key] for key in config["features"]["types"]])
                    mspc_rt.mspc([noc_path], test, starttime, endtime, window_size=config["features"]["window_size"],
                                window_shift=config["features"]["window_shift"], missing_rates=features["missing_rates"],
                                plot=False, update_log=False, nocs_path=config["paths"]["nocs"], verbose=False)

            with st.spinner("Plotting results..."):
                plots.plot_tscore(noc_name, starttime.replace(tzinfo=timezone.utc), endtime.replace(tzinfo=timezone.utc),
                                    T_weight=weight, logscale=logscale, n_consecutive=n_consecutive, nocs_path = config["paths"]["nocs"])
