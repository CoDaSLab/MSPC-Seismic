import streamlit as st
from config.init import init_page, init_session_state

from widgets import *
from utils.functions import load_stations

import os
from datetime import datetime
import json

# --- Application start ---
init_page("Configuration")
init_session_state()
st.title("Configuration")
# ------------------------

config = st.session_state.config
config_path = st.session_state.config_path

key = "config_form"
new_config = config
station_list = load_stations()

with st.form(key):
    st.subheader("Directories and log files")
    col1, col2 = st.columns(2)
    with col1:
        new_config["paths"]["data"] = st.text_input("Raw signal data directory", value=config["paths"]["data"])
        new_config["paths"]["features"] = st.text_input("Features directory", value=config["paths"]["features"])
        new_config["paths"]["nocs"] = st.text_input("NOCs directory", value=config["paths"]["nocs"])
    with col2:
        new_config["paths"]["plots"] = st.text_input("Plots directory", value=config["paths"]["plots"])
        new_config["paths"]["latest_pulls_log"] = st.text_input("Latest pulls log file", value=config["paths"]["latest_pulls_log"])
        new_config["paths"]["noc_log"] = st.text_input("NOC log file", value=config["paths"]["noc_log"])
        new_config["paths"]["anomaly_log"] = st.text_input("Anomaly log file", value=config["paths"]["anomaly_log"])
    
    st.subheader("Stations and channels")
    new_config["data"]["network"] = st.text_input("Network", value=config["data"]["network"], disabled=True)
    new_config["data"]["stations"], new_config["data"]["channels"] = forms.multi_select_station(key, station_list, default_stations=config["data"]["stations"], 
                                                                              default_channels=config["data"]["channels"])
    
    st.subheader("Real-time monitoring")
    col1, col2 = st.columns(2)
    with col1:
        col = st.columns(2)
        with col[0]:
            new_config["monitoring"]["auto_monitoring"] = st.checkbox("Enable real-time monitoring", value=config["monitoring"]["auto_monitoring"])
        with col[1]:
            other.monitoring_status()        
        new_config["monitoring"]["update_frequency"] = st.number_input("Update frequency (in minutes)", value=config["monitoring"]["update_frequency"], min_value=0)
        new_config["monitoring"]["delay"] = st.number_input("Delay (in minutes)", value=config["monitoring"]["delay"], min_value=0)
        new_config["monitoring"]["num_days_before_delete"] = st.number_input("Time before deletion (in days)", value=float(config["monitoring"]["num_days_before_delete"]), min_value=0.0,
                                                        step=1.0, help="Saved features, NOCs and graphs will be deleted after the specified number of days.")
    with col2:
        with col[0]:
            new_config["monitoring"]["plots"]["save"] = st.checkbox("Save plots?", value=config["monitoring"]["plots"]["save"],
                                                                    help = "If checked, all plots generated will be saved in the specified path.")
        with col[1]:
            new_config["monitoring"]["verbose"] = st.checkbox("Detailed logs", value=config["monitoring"]["verbose"],
                                                            help="Include more details in the monitoring log files")
        new_config["monitoring"]["plots"]["num_hours"] = st.number_input("Time range of the saved plots (in hours)", value=float(config["monitoring"]["plots"]["num_hours"]), min_value=0.0, step=1.0)
        new_config["monitoring"]["num_days_noc_update_frequency"] = st.number_input("NOC update frequency (in days)", value=float(config["monitoring"]["num_days_noc_update_frequency"]), min_value=0.0, step=1.0)
        new_config["monitoring"]["num_days_noc_length"] = st.number_input("Time range of NOC data (in days)", value=float(config["monitoring"]["num_days_noc_length"]), min_value=0.0, step=1.0)

    
    st.subheader("Feature extraction parameters")
    col1, col2 = st.columns(2)
    with col1:
        new_config["features"]["window_size"] = st.number_input("Window size (in seconds)", value=config["features"]["window_size"], min_value=1)
        new_config["features"]["window_shift"] = st.number_input("Window shift (in seconds)", value=config["features"]["window_shift"] 
                                                                    if config["features"]["window_shift"] else new_config["features"]["window_size"],
                                                        help="Time between the start of two consecutive windows. A window shift equal to the window size means no overlap between windows.")
        new_config["features"]["windowing"] = forms.select_windowing(key, default=config["features"]["windowing"])

    with col2:
        new_config["features"]["detrend"] = forms.select_detrend(key, default=config["features"]["detrend"])
        # feature_options = ["spectrogram_unfold"]
        # new_config["features"]["types"] = st.multiselect("Select feature types", options=feature_options, default=feature_options[0],
        #                                 help="Available feature types are FFT coefficients and derivatives.")
        fft_auto = st.checkbox("Set FFT points automatically", value=True)
        new_config["features"]["stft_params"]["fft_points"] = forms.select_FFT_points(key, new_config["features"]["window_size"])
        if fft_auto:
            new_config["features"]["stft_params"]["fft_points"] = 'auto'

    
    with st.expander("Signal processing settings"):
        new_config["features"]["merge_method"] = st.number_input("Merge method", value=config["features"]["merge_method"], min_value=0, max_value=2, step=1,
                                                help="Method for merging traces with gaps and overlaps. Follows the ObsPy notation: " \
                                                "https://docs.obspy.org/packages/autogen/obspy.core.trace.Trace.html#obspy.core.trace.Trace.__add__")
        new_config["features"]["merge_fill_value"] = st.text_input("Merge fill value", value=config["features"]["merge_fill_value"],
                                                help="Value to fill gaps in the middle of a signal when merging traces. Follows the ObsPy notation: " \
                                                "https://docs.obspy.org/packages/autogen/obspy.core.trace.Trace.html#obspy.core.trace.Trace.__add__")
        new_config["features"]["pad_fill_value"] = st.number_input("Pad fill value", value=config["features"]["pad_fill_value"],
                                                help="Value to fill gaps at the beginning or end of a signal.")

    
    submitted = st.form_submit_button("Save configuration", type="primary", use_container_width=True)
    if submitted:
        if len(new_config["data"]["stations"]) < 1:
            st.error("Select at least one station.")
        elif len(new_config["data"]["channels"]) < 1:
            st.error("Select at least one channel.")
        else:
            with st.spinner("Saving configuration..."):
                # Save backup
                backup_folder = os.path.join(os.path.dirname(config_path), "backups/config/")
                new_config["metadata"]["running"] = False
                os.makedirs(backup_folder, exist_ok=True)
                with open(backup_folder + "config_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json", "w") as f:
                    json.dump(config, f, indent=4)

                # Save new configuration file
                with open(config_path, "w") as f:
                    json.dump(new_config, f, indent=4)
            st.session_state.config = new_config
            if not new_config["monitoring"]["auto_monitoring"]:
                st.warning("Real-time monitoring is disabled.", icon="⚠️")
            st.success("Configuration saved successfully.", icon = "✔️")

st.header("Current configuration")
st.json(config)
