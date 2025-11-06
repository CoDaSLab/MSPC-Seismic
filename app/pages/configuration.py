import streamlit as st
from config.init import init_page, init_session_state

from widgets import *
from utils.functions import get_channels, load_stations

import os
import re
import numpy as np
from datetime import datetime, timezone
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
station_list = load_stations(column="code")
channels = get_channels()

with st.form(key):
    st.subheader("Directories and log files")
    col1, col2 = st.columns(2)
    with col1:
        new_config["paths"]["data"] = st.text_input("Raw signal data directory", value=config["paths"]["data"])
        new_config["paths"]["features"] = st.text_input("Features directory", value=config["paths"]["features"])
        new_config["paths"]["nocs"] = st.text_input("NOCs directory", value=config["paths"]["nocs"])
        new_config["paths"]["plots"] = st.text_input("Plots directory", value=config["paths"]["plots"])
    with col2:
        new_config["paths"]["latest_pulls_log"] = st.text_input("Latest pulls log file", value=config["paths"]["latest_pulls_log"])
        new_config["paths"]["noc_log"] = st.text_input("NOC log file", value=config["paths"]["noc_log"])
        new_config["paths"]["anomaly_log"] = st.text_input("Anomaly log file", value=config["paths"]["anomaly_log"])
        new_config["paths"]["station_catalog"] = st.text_input("Station catalog file", value=config["paths"]["station_catalog"])
    
    st.subheader("Real-time monitoring")
    col1, col2 = st.columns(2)
    with col1:
        col = st.columns(2)
        with col[0]:
            if 'previous_auto_monitoring' not in st.session_state:
                st.session_state.previous_auto_monitoring = config["monitoring"]["auto_monitoring"]
            new_config["monitoring"]["auto_monitoring"] = st.toggle("Enable real-time monitoring", value=config["monitoring"]["auto_monitoring"])
        with col[1]:
            other.monitoring_status()        
        new_config["monitoring"]["update_frequency"] = st.number_input("Update frequency (in minutes)", value=config["monitoring"]["update_frequency"], min_value=0)
        new_config["monitoring"]["delay"] = st.number_input("Delay (in minutes)", value=config["monitoring"]["delay"], min_value=0)
        new_config["monitoring"]["num_days_before_delete"] = st.number_input("Time before deletion (in days)", value=float(config["monitoring"]["num_days_before_delete"]), 
                                                                min_value=float(config["monitoring"]["num_days_noc_length"] + 1),
                                                                step=1.0, help="Saved features, mSEED files and NOCs will be deleted after the specified number of days. " \
                                                                    "It cannot be lower than the training period length")
    with col2:
        with col[0]:
            new_config["monitoring"]["plots"]["save"] = st.checkbox("Save plots?", value=config["monitoring"]["plots"]["save"],
                                                                    help = "If checked, all plots generated will be saved in the specified path.")
        with col[1]:
            new_config["monitoring"]["verbose"] = st.checkbox("Detailed logs", value=config["monitoring"]["verbose"],
                                                            help="Include more details in the monitoring log files")
        new_config["monitoring"]["plots"]["num_hours"] = st.number_input("Time range of the saved plots (in hours)", value=float(config["monitoring"]["plots"]["num_hours"]), min_value=0.0, step=1.0)
        new_config["monitoring"]["num_days_noc_update_frequency"] = st.number_input("Training update frequency (in days)", value=float(config["monitoring"]["num_days_noc_update_frequency"]), min_value=0.0, step=1.0)
        new_config["monitoring"]["num_days_noc_length"] = st.number_input("Time range of training data (in days)", value=float(config["monitoring"]["num_days_noc_length"]), min_value=0.0, step=1.0)

    if station_list is not None: 
        st.subheader("Station groups")
        n_stations = []
        n_channels = []
        group_keys = list(config["groups"].keys())
        for group in group_keys:
            gkey = key + '_' + group
            gname = config["groups"][group]["name"]
            with st.expander(gname):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"##### {gname}")
                    new_config["groups"][group]["name"] = st.text_input("Group name", value=config["groups"][group]["name"], key=gkey + '_name')
                with col2:
                    new_config["groups"][group]["active"] = st.toggle("Real-time monitoring", value=config["groups"][group]["active"], key = gkey + '_active',
                                                                help=f"Choose whether or not group {gname} is monitored in real time.")
                    new_config["groups"][group]["network"] = st.text_input("Network", value=config["groups"][group]["network"], disabled=False, key=gkey + '_network')
                new_config["groups"][group]["stations"], new_config["groups"][group]["channels"] = forms.multi_select_station(gkey, station_list, 
                                                                                                        default_stations=config["groups"][group]["stations"], 
                                                                                                        default_channels=config["groups"][group]["channels"])

                delete_group = st.checkbox("Delete this group? (This action cannot be undone.)", value=False, key=gkey + '_delete')

            if delete_group:
                del new_config["groups"][group]
            else:
                n_stations.append(len(new_config["groups"][group]["stations"]))
                n_channels.append(len(new_config["groups"][group]["channels"]))

                # Change group key according to new name
                new_key = new_config["groups"][group]["name"].lower()
                new_key = re.sub(r'[^a-z0-9 ]', '', new_key)
                new_key = re.sub(r'\s+', '_', new_key.strip())
                new_config["groups"][new_key] = new_config["groups"].pop(group)


    st.subheader("Connection")
    new_config["connection"]["ssh_key_path"] = st.text_input("Path to the SSH key", value=config["connection"]["ssh_key_path"])
    col1, col2 = st.columns(2)
    with col1:
        new_config["connection"]["server_IP"] = st.text_input("Remote server IP address", value=config["connection"]["server_IP"], 
                                                              help="IP address of the server where seismic data are located.")
    with col2:
        new_config["connection"]["server_user"] = st.text_input("Remote server username", value=config["connection"]["server_user"])
    
    with st.expander("MySQL database settings"):
        if 'previous_mysql_update' not in st.session_state:
            st.session_state.previous_mysql_update = config["connection"]["mysql_connection"]["mysql_update"]
        new_config["connection"]["mysql_connection"]["mysql_update"] = st.toggle("Enable connection to database", 
                                                                                value=config["connection"]["mysql_connection"]["mysql_update"],
                                                                                help="The MySQL database is used to automatically update the 'Station catalog' file daily.")
        cols = st.columns(2)
        with cols[0]:
            new_config["connection"]["mysql_connection"]["user"] = st.text_input("MySQL username", 
                                                                                value=config["connection"]["mysql_connection"]["user"])
        with cols[1]:
            # new_config["connection"]["mysql_connection"]["password"] = st.text_input("MySQL password", type="password",
            #                                                                     value=config["connection"]["mysql_connection"]["password"])
            new_config["connection"]["mysql_connection"]["database_name"] = st.text_input("MySQL database name", 
                                                                                        value=config["connection"]["mysql_connection"]["database_name"])
        new_config["connection"]["mysql_connection"]["query"] = st.text_input("MySQL query", 
                                                                                value=config["connection"]["mysql_connection"]["query"])

    st.subheader("Feature extraction parameters")
    col1, col2 = st.columns(2)
    with col1:
        new_config["features"]["window_size"] = st.number_input("Window size (in seconds)", value=config["features"]["window_size"], min_value=1)
        shift_auto = st.checkbox("Set window shift automatically", value=True, help="Window shift is automatically set to the same value as window size when this box is checked.")
        new_config["features"]["window_shift"] = st.number_input("Window shift (in seconds)", value=config["features"]["window_shift"] 
                                                    if config["features"]["window_shift"] else new_config["features"]["window_size"],
                                                    help="Time between the start of two consecutive windows. A window shift equal to the window size means no overlap between windows.")
        if shift_auto:
            window_shift = new_config["features"]["window_size"]
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

    
    with st.expander("Advanced settings: ObsPy settings"):
        new_config["features"]["merge_method"] = st.number_input("Merge method", value=config["features"]["merge_method"], min_value=0, max_value=2, step=1,
                                                help="Method for merging traces with gaps and overlaps. Follows the ObsPy notation: " \
                                                "https://docs.obspy.org/packages/autogen/obspy.core.trace.Trace.html#obspy.core.trace.Trace.__add__")
        new_config["features"]["merge_fill_value"] = st.text_input("Merge fill value", value=config["features"]["merge_fill_value"],
                                                help="Value to fill gaps in the middle of a signal when merging traces. Follows the ObsPy notation: " \
                                                "https://docs.obspy.org/packages/autogen/obspy.core.trace.Trace.html#obspy.core.trace.Trace.__add__")
        new_config["features"]["pad_fill_value"] = st.number_input("Pad fill value", value=config["features"]["pad_fill_value"],
                                                help="Value to fill gaps at the beginning or end of a signal.")
    
    with st.expander("Advanced settings: Default model training parameters"):
        new_config["features"]["noc_params"]["preprocessing"] = forms.select_preprocessing(key)
        new_config["features"]["noc_params"]["n_components"] = st.number_input("Number of components", min_value=1, 
                                                                               value=config["features"]["noc_params"]["n_components"])
        new_config["features"]["noc_params"]["quantile_threshold"] = st.number_input("Quantile", min_value=0.0, max_value=1.0,
                                                                                     value=config["features"]["noc_params"]["quantile_threshold"],
                                                                                     help="Quantile to be used as threshold for anomaly detection.")
          
    submitted = st.form_submit_button("Save configuration", type="primary", use_container_width=True)

if submitted:
    if station_list is not None and any(np.array(n_stations) == 0):
        idx0 = n_stations.index(0)
        g = list(new_config["groups"].keys())[idx0]
        gname = config["groups"][g]["name"]
        st.error(f"Select at least one station for group {gname}.")
    elif station_list is not None and any(np.array(n_channels) == 0):
        idx0 = n_channels.index(0)
        g = list(new_config["groups"].keys())[idx0]
        gname = config["groups"][g]["name"]
        st.error(f"Select at least one channel for group {gname}.")
    else:
        with st.spinner("Saving configuration..."):
            # Save backup
            backup_folder = os.path.join(os.path.dirname(config_path), "backups/config/")
            new_config["metadata"]["running"] = False
            new_config["metadata"]["creation_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            os.makedirs(backup_folder, exist_ok=True)
            with open(backup_folder + "config_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json", "w") as f:
                json.dump(config, f, indent=4)

            # Save new configuration file
            with open(config_path, "w") as f:
                json.dump(new_config, f, indent=4)
            
            # Relaunch cron_setup if the update frequency or mysql integration changed
            if new_config["connection"]["mysql_connection"]["mysql_update"] != st.session_state.previous_mysql_update \
                or new_config["monitoring"]["auto_monitoring"] != st.session_state.previous_auto_monitoring:
                import subprocess
                result = subprocess.run(["python", "installation/cron_setup.py"], capture_output=True, text=True)
                
                print(result.stdout)
                
        st.session_state.config = new_config
        if not new_config["monitoring"]["auto_monitoring"]:
            st.warning("Real-time monitoring is disabled.", icon="⚠️")
        st.success("Configuration saved successfully.", icon = "✔️")


# Add new group
if station_list is not None:
    with st.expander("Create a new group"):
        with st.form("Select the new group's parameters"):
            new_g = {}
            col1, col2 = st.columns(2)
            with col1:
                new_g["name"] = st.text_input("Group name", value="New group")

                # Generate group key
                new_key = new_g["name"].lower()
                new_key = re.sub(r'[^a-z0-9 ]', '', new_key)
                group = re.sub(r'\s+', '_', new_key.strip())
                gkey = group

                new_g["active"] = st.toggle("Real-time monitoring", value=True, key = gkey + '_active',
                                            help=f"Choose whether or not group {new_g["name"]} is monitored in real time.")
            with col2:
                new_g["network"] = st.text_input("Network", value=st.session_state.group["network"], 
                                                disabled=False, key=gkey + '_network')
            new_g["stations"], new_g["channels"] = forms.multi_select_station(gkey, station_list, 
                                                                            default_stations=st.session_state.group["stations"], 
                                                                            default_channels=st.session_state.group["channels"])

            n_stations.append(len(new_g["stations"]))
            n_channels.append(len(new_g["channels"]))

            created_group = st.form_submit_button("Create group", type="primary", use_container_width=True)

        if created_group:
            if len(new_g["stations"]) == 0:
                st.error(f"Select at least one station for the new group.")
            elif len(new_g["channels"]) == 0:
                st.error(f"Select at least one channel for the new group.")
            else:
                new_config_g = config
                new_config_g["groups"][group] = new_g
                with st.spinner("Saving configuration..."):
                    # Save backup
                    backup_folder = os.path.join(os.path.dirname(config_path), "backups/config/")
                    new_config_g["metadata"]["running"] = False
                    new_config_g["metadata"]["creation_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    os.makedirs(backup_folder, exist_ok=True)
                    with open(backup_folder + "config_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json", "w") as f:
                        json.dump(config, f, indent=4)

                    # Save new configuration file
                    with open(config_path, "w") as f:
                        json.dump(new_config_g, f, indent=4)
                st.session_state.config = new_config_g
                st.success("New group created successfully. Configuration updated.", icon = "✔️")

# st.header("Current configuration")
# st.json(config)
