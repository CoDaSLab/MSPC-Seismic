import streamlit as st
from config.init import init_page, init_session_state
from config.interface import header_monitoring

from widgets import *

from preprocessing.fft_rt import calculate_fft_rt
from monitoring import mspc_rt, utils
from monitoring.NOC import NOC

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

_, default_endtime_test = utils.start_and_end_times(datetime.now(timezone.utc), 
                                            update_frequency=config["monitoring"]["update_frequency"],
                                            delay = 2*config["monitoring"]["delay"])
default_starttime_test = default_endtime_test - timedelta(hours=config["monitoring"]["plots"]["num_hours"])
if "start_date" not in st.session_state:
    st.session_state.start_date = default_starttime_test
    st.session_state.start_time = default_starttime_test
    st.session_state.end_date = default_endtime_test
    st.session_state.end_time = default_endtime_test

exploration_on = False
key = "on_demand"
COL = st.columns(2)

with COL[0]:
    current_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    noc_start_day = current_day - timedelta(days=config["monitoring"]["num_days_noc_length"])

    with st.form(key + "selector"):
        st.write("##### Select stations and channels:")
        network = config["data"]["network"]
        stations, channels = forms.multi_select_station(key, station_list=config["data"]["stations"])
        stations = sorted(stations)
        channels = sorted(channels)
        st.write("##### Select training time range:")
        starttime_train, endtime_train = forms.select_time(key + '_train', default_start=noc_start_day, default_end=current_day)

        st.write("##### Select test time range:")
        starttime_test, endtime_test = forms.select_time(key + "_test", default_start=default_starttime_test, 
                                                         default_end=default_endtime_test)
        
        subcol = st.columns(2)
        with subcol[0]:
            logscale = st.checkbox("Log scale", value=True, key = key + "logscale",
                                help="Display Y-axis using a logarithmic scale.")
        with subcol[1]:
            n_consecutive = st.number_input("Number of minimum consecutive windows over threshold", min_value=1, value=3,
                                    key = key + "consecutive_windows", 
                                    help="When the number of consecutive windows over the threshold is greater or equal than this number, " \
                                    "the corresponding windows will be colored red in the graph.")
        weight = st.slider("T-score weight", 0.0, 1.0, step=0.025, value=0.5)

        with st.expander("Additional parameters"):
            st.write("##### Extraction parameters:")
            window, shift = forms.select_window(key)

            col = st.columns(2)
            with col[0]:
                detrend = forms.select_detrend(key, default=config["features"]["detrend"])
                windowing = forms.select_windowing(key, default=config["features"]["windowing"])
            with col[1]:
                fft_auto = st.checkbox("Set FFT points automatically", value=True)
                fft_points = forms.select_FFT_points(key, window)
                if fft_auto:
                    fft_points = 'auto'
            
            # NOC parameters
            st.write("##### NOC parameters:")
            col = st.columns(2)
            with col[0]:
                prep = forms.select_preprocessing(key)
            with col[1]:
                quantile = st.number_input("Quantile", min_value=0.0, value=0.99, max_value=1.0,
                                            help="Quantile to be used as threshold for anomaly detection.")
            
        submit = st.form_submit_button("Plot", type = "primary", use_container_width=True)

# Calculate and display T-score
with COL[1]:
    if submit:
        st.session_state.tscore_plot = False
        if len(stations) == 0 or len(channels) == 0:
            st.error("Please select at least one station and channel.")
        elif starttime_test >= endtime_test or starttime_train >= endtime_train:
            st.error("Start time cannot be after end time.")
        else:
            add_match = {'start_time': starttime_train.strftime('%Y-%m-%dT%H:%M:%SZ'), 'end_time': endtime_train.strftime('%Y-%m-%dT%H:%M:%SZ'), 
                        'window_size':window, 'window_shift':shift, 'detrend':detrend, 'windowing':windowing, 'fft_points': fft_points}
            nocs_and_sts = utils.check_nocs(config["paths"]["noc_log"], stations, noc_types=('static', 'dynamic', 'inactive', 'exploratory'),
                                            additional_matches=add_match, nocs_path=config["paths"]["nocs"])
            
            if len(stations) == 1:
                nocs_available = [noc for noc, _ in nocs_and_sts]
            else:
                nocs_available = [noc for noc, st in nocs_and_sts if isinstance(st, list) and st == stations]
            
            if len(nocs_available) > 0:
                noc_name = nocs_available[0]
                # st.success(f"An existing trained model ({noc_name}) for this period will be used.")
            else:
                # st.warning(f"No trained model for this period was found. A new one will be created.")
                with st.spinner("Calculating training features..."):
                    noc_name = "-".join(stations) + '_e_' + endtime_test.strftime("%Y-%m-%d")
                    features_train = calculate_fft_rt(starttime_train, endtime_train, network, stations, channels,
                                                window, shift, detrend, windowing, fft_points, merge_method=config["features"]["merge_method"],
                                                merge_fill_value=config["features"]["merge_fill_value"], pad_fill_value=config["features"]["pad_fill_value"], 
                                                data_path=config["paths"]["data"])
                with st.spinner("Training model..."):
                    noc = NOC(noc_name, features_train["spectrogram_unfold"], features_train["times_label"], network=network, 
                              station=stations if len(stations)>1 else stations[0], channels=channels,
                              type='exploratory', preprocessing=prep, n_components=1, quantile_threshold=quantile, 
                              csv_path=config["paths"]["noc_log"])
                    noc.set_metadata(starttime_train, endtime_train, window, shift, detrend, windowing, fft_points, merge_method=config["features"]["merge_method"],
                                    merge_fill_value=config["features"]["merge_fill_value"], pad_fill_value=config["features"]["pad_fill_value"])
                    noc.save(os.path.join(config["paths"]["nocs"], noc_name).replace('\\', '/'))

            with st.spinner("Calculating test features..."):
                nocs_path = st.session_state.config["paths"]["nocs"]
                noc = NOC.load(os.path.join(nocs_path, noc_name))
                metadata = noc.metadata
                features_test = calculate_fft_rt(starttime_test, endtime_test, network=network, stations=stations, 
                                                channels=channels, window_length=metadata["window_size"],
                                                window_shift=metadata["window_shift"], detrend=metadata["detrend"],
                                                windowing=metadata["windowing"], n_bins=metadata["fft_points"], 
                                                merge_method=metadata["merge_method"], merge_fill_value=metadata["merge_fill_value"],
                                                pad_fill_value=metadata["pad_fill_value"], data_path=config["paths"]["data"])

            with st.spinner("Perfoming MSPC..."):
                noc_path = os.path.join(config["paths"]["nocs"], noc_name)
                mspc_rt.mspc([noc_path], features_test["spectrogram_unfold"], starttime_test, endtime_test, window_size=metadata["window_size"],
                            window_shift=metadata["window_shift"], missing_rates=features_test["missing_rates"],
                            plot=False, update_log=False, nocs_path=config["paths"]["nocs"], verbose=False)
            
            st.session_state.tscore_kwargs = {'noc_name':noc_name, 'starttime':starttime_test.replace(tzinfo=timezone.utc), 
                                                'endtime': endtime_test.replace(tzinfo=timezone.utc), 'T_weight':weight, 'logscale':logscale,
                                                'n_consecutive':n_consecutive, 'nocs_path':nocs_path}
            st.session_state.tscore_plot = True

    if 'tscore_plot' in st.session_state and st.session_state.tscore_plot:
        with st.spinner("Plotting results..."):
            selected_points = plots.plot_tscore(**st.session_state.tscore_kwargs, key=key + "_tscore")

        # Perform oMEDA with selected points
        try:
            if selected_points["selection"]["points"]:
                exploration_on = True
                st.subheader("oMEDA")

                nocs_path = st.session_state.config["paths"]["nocs"]
                noc = NOC.load(os.path.join(nocs_path, st.session_state.tscore_kwargs["noc_name"]))
                station_list = noc.station
                starttime = selected_points["selection"]["points"][0]["x"]
                endtime = selected_points["selection"]["points"][-1]["x"]
                try:
                    starttime = datetime.strptime(starttime, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                except: starttime = datetime.strptime(starttime, "%Y-%m-%d %H:%M").strftime("%Y-%m-%d %H:%M:%S")
                try:
                    endtime = datetime.strptime(endtime, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                except: endtime = datetime.strptime(endtime, "%Y-%m-%d %H:%M").strftime("%Y-%m-%d %H:%M:%S")
                with st.spinner("Calculating oMEDA..."):
                    omeda_vec, freqs_label, channel_class, stations_class = noc.omeda(starttime, endtime, nocs_path)
                    fig = plots.plot_omeda(omeda_vec, stations_class, channel_class, freqs_label, logscale=False)

                st.plotly_chart(fig, key=key + 'omeda', use_container_width=True)
        except Exception as e: 
            st.error(f"Error computing oMEDA: {e}")
    
# Extra visualizations
if exploration_on:
    other.exploration(starttime, endtime, station_list)
