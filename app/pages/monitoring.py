import streamlit as st
from config.init import init_page, init_session_state
from config.interface import header_monitoring

from widgets import *
from utils.functions import get_stations

from preprocessing.fft_rt import calculate_fft_rt, find_features
from monitoring import mspc_rt, utils
from monitoring.NOC import NOC, fuse_nocs

import json
import numpy as np
import os
from datetime import datetime, timezone, timedelta
from scipy.io import savemat

# --- Application start ---
init_page("Monitoring - Visualization")
init_session_state()
st.title("Monitoring")
header_monitoring()
# ------------------------

# On-demand
st.subheader("On-demand visualization")

config = st.session_state.config
group = st.session_state.group

key = "on_demand"

if 'rt_stations' not in st.session_state:
    st.session_state.rt_stations = group["stations"]

if "default_starttime_test" not in st.session_state:
    _, st.session_state.default_endtime_test = utils.start_and_end_times(datetime.now(timezone.utc), 
                                                                        update_frequency=config["monitoring"]["update_frequency"],
                                                                        delay = 2*config["monitoring"]["delay"])
    st.session_state.default_starttime_test = st.session_state.default_endtime_test - timedelta(hours=config["monitoring"]["plots"]["num_hours"])
    st.session_state.start_date = st.session_state.default_starttime_test
    st.session_state.start_time = st.session_state.default_starttime_test
    st.session_state.end_date = st.session_state.default_endtime_test
    st.session_state.end_time = st.session_state.default_endtime_test

exploration_on = False
COL = st.columns(2)

with COL[0]:
    current_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    noc_start_day = current_day - timedelta(days=config["monitoring"]["num_days_noc_length"])

    with st.form(key + "selector"):
        st.write("##### Select stations and channels:")
        network = group["network"]
        stations, channels = forms.multi_select_station(key, station_list=get_stations(group["name"]), 
                                                        default_stations=st.session_state.rt_stations, default_channels=group["channels"])
        stations = sorted(stations)
        channels = sorted(channels)
        st.write("##### Select training time range:")
        starttime_train, endtime_train = forms.select_time(key + '_train', default_start=noc_start_day, default_end=current_day)

        st.write("##### Select test time range:")
        starttime_test, endtime_test = forms.select_time(key + "_test", default_start=st.session_state.default_starttime_test, 
                                                         default_end=st.session_state.default_endtime_test)
        st.session_state.default_starttime_test = starttime_test
        st.session_state.default_endtime_test = endtime_test
        
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
            # Parameter dictionaries for NOC and features metadata
            config_temp = config
            config_temp["features"]["window_size"] = window
            config_temp["features"]["window_shift"] = shift
            config_temp["features"]["detrend"] = detrend
            config_temp["features"]["windowing"] = windowing
            config_temp["features"]["stft_params"]["fft_points"] = fft_points
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
                noc_name = "-".join(stations) + '_e_' + endtime_train.strftime("%Y-%m-%d")
                indiv_noc_names = []
                for sta in stations:
                    indiv_noc_name = sta + '_e_' + endtime_test.strftime("%Y-%m-%d")
                    with st.spinner(f"Calculating training features for station {sta}..."):
                        features_train = calculate_fft_rt(starttime_train, endtime_train, network, sta, channels,
                                                        window, shift, detrend, windowing, fft_points, merge_method=config["features"]["merge_method"],
                                                        merge_fill_value=config["features"]["merge_fill_value"], pad_fill_value=config["features"]["pad_fill_value"], 
                                                        data_path=config["paths"]["data"])
                            
                    with st.spinner(f"Training model for station {sta}..."):
                        noc = NOC(indiv_noc_name, features_train["spectrogram_unfold"], features_train["times_label"], network=network, 
                                  station=sta, channels=channels, type='exploratory', preprocessing=prep, 
                                  n_components=config["features"]["noc_params"]["n_components"], quantile_threshold=quantile, 
                                  csv_path=config["paths"]["noc_log"])
                        noc.set_metadata(starttime_train, endtime_train, window, shift, detrend, windowing, fft_points, merge_method=config["features"]["merge_method"],
                                         merge_fill_value=config["features"]["merge_fill_value"], pad_fill_value=config["features"]["pad_fill_value"])
                        noc.save(os.path.join(config["paths"]["nocs"], indiv_noc_name).replace('\\', '/'))
                    
                    indiv_noc_names.append(indiv_noc_name)
                
                if len(stations) > 1:
                    with st.spinner("Training model for all stations..."):
                        # Create combined NOC
                        noc = fuse_nocs(indiv_noc_names, new_type='exploratory', n_components=config["features"]["noc_params"]["n_components"])
                        noc.set_metadata(starttime_train, endtime_train, window, shift, detrend, windowing, fft_points, merge_method=config["features"]["merge_method"],
                                            merge_fill_value=config["features"]["merge_fill_value"], pad_fill_value=config["features"]["pad_fill_value"])
                        noc.save(os.path.join(config["paths"]["nocs"], noc_name).replace('\\', '/'))

            for sta in stations:
                with st.spinner(f"Calculating test features for station {sta}..."):
                    nocs_path = st.session_state.config["paths"]["nocs"]
                    noc = NOC.load(os.path.join(nocs_path, noc_name))
                    metadata = noc.metadata
                    features_test = calculate_fft_rt(starttime_test, endtime_test, network=network, stations=sta, 
                                                    channels=channels, window_length=metadata["window_size"],
                                                    window_shift=metadata["window_shift"], detrend=metadata["detrend"],
                                                    windowing=metadata["windowing"], n_bins=metadata["fft_points"], 
                                                    merge_method=metadata["merge_method"], merge_fill_value=metadata["merge_fill_value"],
                                                    pad_fill_value=metadata["pad_fill_value"], data_path=config["paths"]["data"])
                    # Save features files
                    features_test['config'] = json.dumps(config_temp)
                    file_name = sta + '_' + starttime_test.strftime('%Y-%m-%dT%H-%M-%SZ') + '_' + endtime_test.strftime('%Y-%m-%dT%H-%M-%SZ') + '.mat'
                    mat_path = os.path.join(config["paths"]["features"], file_name).replace('\\', '/')
                    savemat(mat_path, features_test)

            with st.spinner("Perfoming MSPC..."):
                noc_path = os.path.join(config["paths"]["nocs"], noc_name)
                del add_match["start_time"], add_match["end_time"], add_match["fft_points"]
                features = find_features(config["paths"]["features"], stations, 
                                         starttime_test.replace(tzinfo=timezone.utc), endtime_test.replace(tzinfo=timezone.utc), 
                                         feature_types=["spectrogram_unfold"], additional_matches=add_match, max_missing_rate=1, 
                                         force_all_stations=True, verbose=True)
        
                if features:
                    # Perform MSPC for all NOCs associated with the station
                    test_data = features["spectrogram_unfold"]
                    mspc_rt.mspc([noc_path], features["spectrogram_unfold"], starttime_test, endtime_test, window_size=metadata["window_size"],
                                window_shift=metadata["window_shift"], missing_rates=features["missing_rates"],
                                plot=False, update_log=False, nocs_path=config["paths"]["nocs"], verbose=False)
                    
                    st.session_state.tscore_kwargs = {'noc_name':noc_name, 'starttime':starttime_test.replace(tzinfo=timezone.utc), 
                                                        'endtime': endtime_test.replace(tzinfo=timezone.utc), 'T_weight':weight, 'logscale':logscale,
                                                        'n_consecutive':n_consecutive, 'nocs_path':nocs_path}
                    st.session_state.tscore_plot = True
                else:
                    st.error("Test features not found.")

    if 'tscore_plot' in st.session_state and st.session_state.tscore_plot:
        with st.spinner("Plotting results..."):
            selected_points = plots.plot_tscore(**st.session_state.tscore_kwargs, key=key + "_tscore")

        # Perform oMEDA with selected points
        try:
            if selected_points["selection"]["points"]:
                st.subheader("oMEDA")

                nocs_path = st.session_state.config["paths"]["nocs"]
                noc = NOC.load(os.path.join(nocs_path, st.session_state.tscore_kwargs["noc_name"]))
                n_components = None

                omeda_options =  ["PCA model", "Residuals", "All"]
                omeda_opt = st.segmented_control("Compare data by:", omeda_options, selection_mode='single', 
                                                    default = omeda_options[1], key = key + 'component_omeda')

                if omeda_opt == omeda_options[0]:
                    n_components = noc.n_components
                elif omeda_opt == omeda_options[1]:
                    n_components = np.arange(noc.n_components + 1, noc.features_shape[1] + 1)
                elif omeda_opt == omeda_options[2]:
                    n_components = noc.features_shape[1]
                else:
                    st.error("Please select an option.")
                
                if n_components is not None:
                    exploration_on = True

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
                        omeda_vec, freqs_label, channel_class, stations_class, missing_stations = noc.omeda(starttime, endtime, n_components)
                        fig = plots.plot_omeda(omeda_vec, stations_class, channel_class, freqs_label, logscale=False,
                                                missing_stations=missing_stations)
                        if len(missing_stations) > 0:
                            st.warning(f"Missing data for station{'s' if len(missing_stations)>1 else ''} {', '.join(missing_stations)} in the selected period.")

                    st.plotly_chart(fig, key=key + 'omeda', use_container_width=True)
        except Exception as e: 
            st.error(f"Error computing oMEDA: {e}")
    
# Extra visualizations
if exploration_on:
    other.exploration(starttime, endtime, station_list, key=key + '_exploration')
