import streamlit as st

def select_sensor(key):
    sensors =  ['PPMA', 'PLPI']
    channels = ['HHE', 'HHN', 'HHZ']
    col = st.columns(2)
    sensor = col[0].selectbox('Sensor', sensors, key=f"sensor_{key}",
                              index = sensors.index(st.session_state.sensor))
    channel = col[1].selectbox('Channel', channels, key=f"channel_{key}",
                               index = channels.index(st.session_state.channel))

    st.session_state.sensor = sensor
    st.session_state.channel = channel

    return sensor, channel

def multi_select_sensor(key):
    sensors =  ['PPMA', 'PLPI']
    channels = ['HHE', 'HHN', 'HHZ']
    col = st.columns(2)
    sensors = col[0].multiselect('Sensors', sensors, key=f"sensor_{key}",
                                default=sensors)
    channels = col[1].multiselect('Channels', channels, key=f"channel_{key}",
                                 default=channels)

    return sensors, channels


def select_time(key):
    from datetime import datetime, time

    col = st.columns(2)
    start_date = col[0].date_input("Select a start day", key=f'start_date_{key}',
                                   value=st.session_state.start_date)
    start_time = col[1].time_input("Select a start time", key=f'start_time_{key}',
                                 value = st.session_state.start_time)

    starttime = datetime.combine(start_date, start_time)
    st.session_state.start_date = start_date
    st.session_state.start_time = start_time

    end_date = col[0].date_input("Select an end day", key=f'end_date_{key}',
                                value=st.session_state.end_date)
    end_time = col[1].time_input("Select an end time", key=f'end_time_{key}', 
                                 value = st.session_state.end_time)
                                 
    endtime = datetime.combine(end_date, end_time)
    st.session_state.end_date = end_date
    st.session_state.end_time = end_time

    return starttime, endtime

def select_detrend(key):
    detrend_options = [None, 'linear', 'simple', 'constant']
    detrend = st.selectbox('Detrend method', detrend_options, key=f"detrend_{key}", index=0,
                           help= "Signals are demeaned on a window basis when calculating the STFT on top of this detrend")
    return detrend


def select_windowing(key):
    import scipy

    windowing_options =  scipy.signal.windows.__all__ 
    if False not in windowing_options:
        windowing_options.append(False)
    windowing = st.selectbox('Windowing:', windowing_options,
                                 len(windowing_options)-1, key=f"windowing_{key}")
    if windowing != False:
        windowing = scipy.signal.windows.__dict__[windowing]

    return windowing

def select_window(key):
    col = st.columns(2) 
    window_size = col[0].number_input('Window length in seconds', value = 60.0,
                    key = f"window_size_{key}")
    window_shift = col[1].number_input('Window overlap in seconds', value = 0.0,
                    key = f"window_shift_{key}")

    return window_size, window_shift

def select_FFT_points(key, window_size = 10, srate = 100):
    FFT_points = st.number_input('Number of frequencies for the FFT',
                                    value = int(window_size*srate),
                                    key = f"FFT_points_{key}")
        

    return FFT_points
