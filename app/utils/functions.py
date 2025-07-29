import pandas as pd

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

def load_stations(filepath = "data/involcan/metadata/stations_all.dat", column_names=["station", "lat", "lon", "height"] ):
    stations = pd.read_csv(filepath, sep=r"\s+",names=column_names)
    return stations

def load_files(filepath="data/involcan/metadata/available_files.csv"):
    files = pd.read_csv(filepath)
    return files

def load_json(filepath="monitoring/config.json"):
    import json
    with open(filepath, 'r') as f:
        config = json.load(f)
    return config

import streamlit as st
import obspy
from obspy.core import UTCDateTime
@st.cache_data
def read_streams(stations, starttime, endtime, channels="HHE", data_path = "data/involcan/mseed/"):
    ST = []
    for station in stations:
        st.write(f"Reading 2021 data for station {station}...")
        stream = obspy.read(f"{data_path}/C7.{station}.*.HHE.*.2021.*",
                        starttime=UTCDateTime(starttime), endtime=UTCDateTime(endtime))
        stream.merge()
        ST.append(stream)
    return ST

def read_noc(noc_name, nocs_path = "data/involcan/nocs/"):
    from monitoring.NOC import NOC
    import os
    
    noc = NOC.load(os.path.join(nocs_path, noc_name).replace('\\', '/'))

    return noc