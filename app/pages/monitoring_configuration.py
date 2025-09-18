import streamlit as st
from config.init import init_page, init_session_state

from widgets import *
from utils.functions import load_data, load_stations

from preprocessing.fft_rt import calculate_fft_rt
from monitoring import NOC, utils

import numpy as np
import os
from datetime import datetime, timezone, timedelta
import pandas as pd
import json

# --- Application start ---
init_page("Monitoring configuration")
init_session_state()
st.title("Monitoring configuration")
# ------------------------

tab = st.tabs(['NOC creator', 'Edit configuration'])

# Configuration file
config = st.session_state.config
config_path = st.session_state.config_path

update_freq = timedelta(minutes=config["general"]["update_frequency"])

starttime, endtime = utils.start_and_end_times(datetime.now(timezone.utc), 
                                        update_frequency=config["general"]["update_frequency"],
                                        delay = config["general"]["delay"])

nocs = utils.get_noc_names(config["paths"]["noc_log"], config["data"]["stations"])
st.session_state.start_date = datetime.date(starttime)
st.session_state.start_time = datetime.time(starttime)
st.session_state.end_date = datetime.date(endtime)
st.session_state.end_time = datetime.time(endtime)

@st.fragment
def noc_maker(config):
    key = 'noc_maker'
    COL = st.columns(2)
    with COL[0]:
        with st.form(key):
            st.subheader("Station and time period:")
            starttime, endtime = forms.select_time(key)
            starttime = pd.Timestamp(starttime, tz='UTC')
            endtime = pd.Timestamp(endtime, tz='UTC')
            
            network = config["data"]["network"]
            station, channels = forms.select_station_multi_channel(key, station_list=config["data"]["stations"], 
                                                                    channel_list=config["data"]["channels"])
            
            st.subheader("Extraction parameters:")
            window, shift = forms.select_window(key)

            col = st.columns(2)
            with col[0]:
                detrend = forms.select_detrend(key)
                windowing = forms.select_windowing(key)
            with col[1]:
                fft_auto = st.checkbox("Set FFT points automatically", value=True)
                fft_points = forms.select_FFT_points(key, window)
                if fft_auto:
                    fft_points = 'auto'

            st.subheader("Features to extract:")
            feature_options = ["ffts", "deltas_ffts", "deltas_deltas_ffts"]
            feature_types = st.multiselect("Select feature types", options=feature_options, default=feature_options[0],
                                            help="Available feature types are FFT coefficients and derivatives.")
            
            # NOC parameters
            st.subheader("NOC parameters:")
            col = st.columns(2)
            with col[0]:
                noc_name = st.text_input("NOC name", help="The end date will be automatically appended to the name.")
                noc_type = st.selectbox("NOC type", options=["dynamic", "static", "inactive", "unavailable"],
                                        help="- dynamic: updates automatically\n- static: does not update automatically\n" \
                                        "- inactive: is not used for real-time monitoring\n- unavailable: makes it invisible to the app")
            with col[1]:
                prep = forms.select_preprocessing(key)
                quantile = st.number_input("Quantile", min_value=0.0, value=0.99, max_value=1.0,
                                            help="Quantile to be used as threshold for anomaly detection.")
            
            submit = st.form_submit_button("Create NOC", use_container_width=True, type="primary")

        if submit:
            with st.spinner("Calculating features..."):
                features = calculate_fft_rt(starttime, endtime, network=network, station=station, 
                                            channels=channels, window_size=window,
                                            window_shift=shift, detrend=detrend,
                                            windowing=windowing, fft_points=fft_points, 
                                            merge_method=config["features"]["merge_method"], merge_fill_value=config["features"]["merge_fill_value"],
                                            pad_fill_value=config["features"]["pad_fill_value"], data_path=config["paths"]["data"], 
                                            cpus=config["features"]["cpus"], verbose=False, save=False)
                
                train_data = np.hstack([features[k] for k in feature_types])
            
            with st.spinner("Creating NOC..."):
                if noc_name == "":
                    noc_name = station + '_' + noc_type[0]
                noc_name = noc_name + '_' + endtime.strftime("%Y-%m-%d")
                st.session_state.noc_name = noc_name
                noc = NOC.NOC(noc_name, train_data, features["obs_labels"], network=network, station=station,
                              type=noc_type, preprocessing=prep, n_components=1,
                              quantile_threshold=quantile, csv_path=config["paths"]["noc_log"])
                
            with st.spinner("Saving NOC..."):
                noc.save(os.path.join(config["paths"]["nocs"], noc_name).replace('\\', '/'))
                noc.write_csv()
            
            st.success("NOC created successfully. Select the number of principal components to complete the NOC's configuration.",
                       icon="✔️")

    with COL[1]:

        # Visualize explained variance by number of components
        with st.expander("Explained variance by number of components", expanded=submit):
            if submit:
                with st.spinner("Calculating..."):
                    plots.plot_var_pca(noc.features, preprocessing=prep)
            else:
                st.write("Create a NOC first.")   

        with st.form(key + "_pca"):
            st.subheader("Select a number of principal components:", help="You need to create a NOC first.")
            col = st.columns(2)
            with col[0]:
                n_components = st.number_input("Number of components", min_value=1, value='min')
            with col[1]:
                submit_dq = st.form_submit_button("Set number of components", disabled=not submit,
                                                type="primary", use_container_width=True)
                  
        if submit_dq:
            with st.spinner("Configuring NOC..."):
                # Update NOC
                noc = NOC.NOC.load(os.path.join(config["paths"]["nocs"], st.session_state.noc_name))
                noc.n_components = n_components
                noc.update()
            
            with st.spinner("Saving changes..."):
                noc.save(os.path.join(config["paths"]["nocs"], st.session_state.noc_name).replace('\\', '/'))
                noc.write_csv()
            
            st.success("NOC configured successfully.", icon="✔️")
    
    with st.expander("NOC list"):
        data = load_data(config["paths"]["noc_log"])
        data = tables.filter_dataframe(data)
        tables.show_table(data)


@st.fragment
def change_config(config, config_path):
    key = "config_form"
    new_config = config
    station_list = load_stations()
    with st.form(key):
        st.header("General parameters")
        col1, col2 = st.columns(2)
        with col1:
            new_config["general"]["update_frequency"] = st.number_input("Update frequency (in minutes)", value=config["general"]["update_frequency"], min_value=0)
            new_config["general"]["delay"] = st.number_input("Delay (in minutes)", value=config["general"]["delay"], min_value=0)
            new_config["paths"]["data"] = st.text_input("Raw signal data directory", value=config["paths"]["data"])
            new_config["paths"]["features"] = st.text_input("Features directory", value=config["paths"]["features"])
            new_config["paths"]["nocs"] = st.text_input("NOCs directory", value=config["paths"]["nocs"])
        with col2:
            new_config["plots"]["save"] = st.checkbox("Save plots?", value=config["plots"]["save"],
                                               help = "If checked, all plots generated will be saved in the specified path.")
            new_config["paths"]["plots"] = st.text_input("Plots directory", value=config["paths"]["plots"])
            new_config["paths"]["latest_pulls_log"] = st.text_input("Latest pulls log file", value=config["paths"]["latest_pulls_log"])
            new_config["paths"]["noc_log"] = st.text_input("NOC log file", value=config["paths"]["noc_log"])
            new_config["paths"]["anomaly_log"] = st.text_input("Anomaly log file", value=config["paths"]["anomaly_log"])
        
        st.header("Stations and channels")
        new_config["data"]["network"] = st.text_input("Network", value=config["data"]["network"], disabled=True)
        new_config["data"]["stations"], new_config["data"]["channels"] = forms.multi_select_station(key, station_list, default_stations=None, 
                                                                                    default_channels=['HHE', 'HHN', 'HHZ'])
        
        st.header("FFT parameters")
        col1, col2 = st.columns(2)
        with col1:
            new_config["features"]["window_size"] = st.number_input("Window size (in seconds)", value=config["features"]["window_size"], min_value=1)
            new_config["features"]["window_shift"] = st.number_input("Window shift (in seconds)", value=config["features"]["window_shift"] if config["features"]["window_shift"] else 0,
                                                         help="Time between the start of two consecutive windows. A window shift equal to the window size means no overlap between windows.")
            new_config["features"]["windowing"] = forms.select_windowing("windowing")
        with col2:
            new_config["features"]["detrend"] = forms.select_detrend("Detrend method")
            feature_options = ["ffts", "deltas_ffts", "deltas_deltas_ffts"]
            new_config["features"]["types"] = st.multiselect("Select feature types", options=feature_options, default=feature_options[0],
                                            help="Available feature types are FFT coefficients and derivatives.")
            fft_auto = st.checkbox("Set FFT points automatically", value=True)
            new_config["features"]["fft_points"] = forms.select_FFT_points(key, new_config["features"]["window_size"])
            if fft_auto:
                new_config["features"]["fft_points"] = 'auto'
        
        with st.expander("Advanced settings"):
            col1, col2 = st.columns(2)
            with col1:
                new_config["features"]["merge_method"] = st.number_input("Merge method", value=config["features"]["merge_method"], min_value=0, max_value=2, step=1,
                                                        help="Method for merging traces with gaps and overlaps. Follows the ObsPy notation: " \
                                                        "https://docs.obspy.org/packages/autogen/obspy.core.trace.Trace.html#obspy.core.trace.Trace.__add__")
                new_config["features"]["merge_fill_value"] = st.text_input("Merge fill value", value=config["features"]["merge_fill_value"],
                                                        help="Value to fill gaps in the middle of a signal when merging traces. Follows the ObsPy notation: " \
                                                        "https://docs.obspy.org/packages/autogen/obspy.core.trace.Trace.html#obspy.core.trace.Trace.__add__")
                new_config["features"]["pad_fill_value"] = st.number_input("Pad fill value", value=config["features"]["pad_fill_value"],
                                                            help="Value to fill gaps at the beginning or end of a signal.")
                new_config["features"]["cpus"] = st.number_input("Number of CPUs for feature extraction", value=config["features"]["cpus"], min_value=1)
            with col2:
                # config["general"]["verbose"] = st.checkbox("verbose", value=config["general"]["verbose"])
                new_config["general"]["num_days_before_delete"] = st.number_input("Time before deletion (in days)", value=config["general"]["num_days_before_delete"], min_value=1,
                                                                help="Saved features, NOCs and graphs will be deleted after the specified number of days.")
                new_config["plots"]["num_hours"] = st.number_input("Time range of the saved plots (in hours)", value=config["plots"]["num_hours"], min_value=1)
                new_config["general"]["num_days_noc_update_frequency"] = st.number_input("NOC update frequency (in days)", value=config["general"]["num_days_noc_update_frequency"], min_value=1)
                new_config["general"]["num_days_noc_length"] = st.number_input("Time range of NOC data (in days)", value=config["general"]["num_days_noc_length"], min_value=1)
        
        submitted = st.form_submit_button("Save configuration", type="primary", use_container_width=True)
        if submitted:
            with st.spinner("Saving configuration..."):
                # Save backup
                backup_folder = os.path.dirpath(config_path) + "/backups/config/"
                os.makedirs(backup_folder, exist_ok=True)
                with open(backup_folder + "config_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json", "w") as f:
                    json.dump(config, f, indent=4)

                # Save new configuration file
                with open(config_path, "w") as f:
                    json.dump(new_config, f, indent=4)
            st.session_state.config = new_config
            st.success("Configuration saved successfully.", icon = "✔️")
    
    st.header("Current configuration")
    st.json(config)



# --------------- NOC creator and editor -----------------
with tab[0]:
    noc_maker(config)

# ------- Configuration tab: Display JSON configuration file --------
# with tab[1]:
#     change_config(config, config_path)
