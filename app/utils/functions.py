import pandas as pd
from config.init import init_session_state
import streamlit as st

init_session_state()
config = st.session_state.config

def load_data(filepath, sep=',', header='infer'):
    return pd.read_csv(filepath,sep=sep, header=header)

def load_events():
    # Load registered events data
    events = pd.read_csv("data/involcan/metadata/ivc.dat", header=None)
    # Name the columns
    events.columns =  ['year', 'month', 'day', 'hour', 'minute', 'second', 'magnitude', 'longitude', 'latitude','depth (km)','*1','*2']
    events = events.drop(["*1","*2"], axis = 1)

    time_col = ['year', 'month', 'day', 'hour', 'minute', 'second']
    events['datetime'] = pd.to_datetime(events[time_col])
    # Discard columns used for datetime
    events = events.drop(time_col, axis=1)
    # Sort by datetime
    events = events.sort_values(by='datetime').reset_index(drop=True)
    # Reorder columns
    events = events[[events.columns[-1]] + list(events.columns[:-1])]
    
    return events

def load_stations(filepath = config["paths"]["station_catalog"], column=None):
    stations = pd.read_csv(filepath, sep=r"\t")

    if column is not None:
        # Return the specified column as a list
        return stations[column].tolist()
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
        last_pulls["latest_pull_time"] = pd.to_datetime(last_pulls["latest_pull_time"], utc=True)
    except FileNotFoundError:
        st.error("No downloaded data from any station.")
        return
    return last_pulls


import streamlit as st
import obspy
from obspy.core import UTCDateTime
@st.cache_data
def read_streams(stations, starttime, endtime, channels=None, data_path = config["paths"]["data"]):
    # Manage string inputs
    if isinstance(stations, str):
        stations = [stations]
    if isinstance(channels, str):
        stations = [channels]

    ST = []
    for station in stations:
        st.write(f"Reading 2021 data for station {station}...")
        st = obspy.Stream()
        if channels is None:
            # Read all channels
            stream = obspy.read(f"{data_path}/C7.{station}.*.*.*.2021.*",
                                    starttime=UTCDateTime(starttime), endtime=UTCDateTime(endtime))
        else:
            for channel in channels:
                stream = obspy.read(f"{data_path}/C7.{station}.*.{channel}.*.2021.*",
                                    starttime=UTCDateTime(starttime), endtime=UTCDateTime(endtime)[0])
                stream = stream.merge()[0]
        
        ST.append(stream)
    return ST

def read_noc(noc_name, nocs_path = config["paths"]["nocs"]):
    from monitoring.NOC import NOC
    import os
    
    noc = NOC.load(os.path.join(nocs_path, noc_name).replace('\\', '/'))

    return noc