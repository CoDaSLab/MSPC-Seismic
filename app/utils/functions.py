import pandas as pd
from config.init import init_session_state
import streamlit as st

init_session_state()
config = st.session_state.config

def load_data(filepath, sep=',', header='infer'):
    return pd.read_csv(filepath,sep=sep, header=header)

def load_stations(filepath = config["paths"]["station_catalog"], column=None):
    try:
        stations = pd.read_csv(filepath, sep="\t")
        if column is not None:
            # Return the specified column as a list
            return stations[column].tolist()
    except FileNotFoundError:
        stations = None
    
    return stations

def get_stations(group=None):
    """
    Reads the configuration file and returns the list of stations for a group. If no group is given, returns all stations.
    """
    groups_dict = config["groups"]  # Groups of stations. Each group has a separate monitoring system
    group_keys = list(groups_dict.keys())
    group_names = [groups_dict[g]["name"] for g in group_keys]

    if group is None:
        stations = []
        for g in groups_dict:
            stations.extend(groups_dict[g]["stations"])
    elif group in group_names:
        idx = group_names.index(group)
        stations = groups_dict[group_keys[idx]]["stations"]
    else:
        raise KeyError(f"Group {group} does not exist.")
    
    return stations

def get_channels(group=None):
    """
    Reads the configuration file and returns the list of stations for a group. If no group is given, returns all stations.
    """
    groups_dict = config["groups"]  # Groups of stations. Each group has a separate monitoring system
    group_keys = list(groups_dict.keys())
    group_names = [groups_dict[g]["name"] for g in group_keys]

    if group is None:
        channels = []
        for g in groups_dict:
            channels.extend(groups_dict[g]["channels"])
    elif group in group_names:
        idx = group_names.index(group)
        channels = groups_dict[group_keys[idx]]["channels"]
    else:
        raise KeyError(f"Group {group} does not exist.")
    
    return channels


def load_last_pulls(filepath=config["paths"]["latest_pulls_log"]):
    try:
        last_pulls = pd.read_csv(filepath)
        last_pulls["latest_pull_time"] = pd.to_datetime(last_pulls["latest_pull_time"], utc=True, 
                                                        format="%Y-%m-%dT%H:%M:%SZ")
    except FileNotFoundError:
        st.error("No downloaded data from any station.")
        return
    return last_pulls


def read_noc(noc_name, nocs_path = config["paths"]["nocs"]):
    from monitoring.NOC import NOC
    import os
    
    noc = NOC.load(os.path.join(nocs_path, noc_name).replace('\\', '/'))

    return noc