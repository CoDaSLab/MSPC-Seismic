import streamlit as st

def select_station(key, station_list, channel_list=['HHE', 'HHN', 'HHZ']):
    col = st.columns(2)
    default_station = station_list.index(st.session_state.station) if st.session_state.station in station_list else 0
    station = col[0].selectbox('Station', station_list, key=f"station_{key}",
                              index = default_station)
    
    default_station = channel_list.index(st.session_state.channel) if st.session_state.channel in channel_list else 0
    channel = col[1].selectbox('Channel', channel_list, key=f"channel_{key}",
                               index = channel_list.index(st.session_state.channel))

    st.session_state.station = station
    st.session_state.channel = channel

    return station, channel

def select_station_multi_channel(key, station_list, channel_list=['HHE', 'HHN', 'HHZ']):
    col = st.columns(2)
    default_station = station_list.index(st.session_state.station) if st.session_state.station in station_list else 0
    station = col[0].selectbox('Station', station_list, key=f"station_{key}",
                              index = default_station)

    channels = col[1].multiselect('Channels', channel_list, key=f"channel_{key}",
                               default = channel_list)

    return station, channels

def multi_select_station(key, station_list, channel_list=['HHE', 'HHN', 'HHZ'],
                         default_stations=None, default_channels=None):
    col = st.columns(2)

    stations = col[0].multiselect('Stations', station_list, key=f"station_{key}",
                                default=default_stations)
    channels = col[1].multiselect('Channels', channel_list, key=f"channel_{key}",
                                default=default_channels)

    return stations, channels

def select_noc(key, stations, noc_log_path = "data/involcan/metadata/noc_list.csv"):
    from monitoring.utils import get_noc_names
    
    col = st.columns(2)
    station = col[0].selectbox('Station', stations, key=f"station_{key}",
                              index = stations.index(st.session_state.station))
    nocs = [noc for noc, st in get_noc_names(noc_log_path, station, noc_types=('static', 'dynamic', 'inactive'))
            if isinstance(st, str)]
    noc = col[1].selectbox('NOC', reversed(nocs), key=f"noc_{key}")

    return station, noc


def select_time(key):
    from datetime import datetime, timedelta

    col = st.columns(2)
    start_date = col[0].date_input("Select a start day", key=f'start_date_{key}',
                                   value=st.session_state.start_date)
    start_time = col[1].time_input("Select a start time", key=f'start_time_{key}',
                                    value = st.session_state.start_time,
                                    step=timedelta(minutes=5))

    starttime = datetime.combine(start_date, start_time)
    st.session_state.start_date = start_date
    st.session_state.start_time = start_time

    end_date = col[0].date_input("Select an end day", key=f'end_date_{key}',
                                value=st.session_state.end_date)
    end_time = col[1].time_input("Select an end time", key=f'end_time_{key}', 
                                 value = st.session_state.end_time,
                                 step=timedelta(minutes=5))
                                 
    endtime = datetime.combine(end_date, end_time)
    st.session_state.end_date = end_date
    st.session_state.end_time = end_time

    return starttime, endtime


def select_time_rt(key):
    from datetime import timedelta

    col = st.columns(2)
    with col[0]:
        hour = st.number_input("Hours", key=f'hour_{key}',
                                min_value=0,
                                max_value=23,
                                value = st.session_state.config["monitoring"]["plots"]["num_hours"])
    with col[1]:
        minute = st.number_input("Minutes", key=f'minute_{key}',
                                min_value=0,
                                max_value=59,
                                value = 0 if hour>0 else 1)
    
    time = timedelta(hours=hour, minutes=minute)
    return time


def select_detrend(key, default=None):
    detrend_options = [None, 'linear', 'simple', 'constant']
    index = detrend_options.index(default)
    detrend = st.selectbox('Detrend method', detrend_options, key=f"detrend_{key}", index=index,
                           help= "Signals are demeaned on a window basis when calculating the STFT on top of this detrend")
    return detrend


def select_windowing(key, default=False):
    import scipy

    windowing_options =  scipy.signal.windows.__all__ 
    if False not in windowing_options:
        windowing_options.append(False)

    index = windowing_options.index(default)
    windowing = st.selectbox('Windowing:', windowing_options, index=index, key=f"windowing_{key}")
    if windowing != False:
        windowing = scipy.signal.windows.__dict__[windowing]

    return windowing

def select_window(key):
    col = st.columns(2) 
    window_size = col[0].number_input('Window length in seconds', value = st.session_state.config["features"]["window_size"],
                    key = f"window_size_{key}")
    window_shift = col[1].number_input('Window shift in seconds', value = st.session_state.config["features"]["window_shift"],
                    key = f"window_shift_{key}")

    return window_size, window_shift

def select_FFT_points(key, window_size = 10, srate = 100):
    FFT_points = st.number_input('Number of frequencies for the FFT',
                                    value = int(window_size*srate),
                                    key = f"FFT_points_{key}")

    return FFT_points

def select_preprocessing(key):
    prep_options = ['mean-centering', 'autoscaling']
    prep = st.selectbox('Preprocessing', prep_options, key=f"preprocess_{key}", index=0)

    prep_num = 1 if prep == 'mean-centering' else 2
    return prep_num
