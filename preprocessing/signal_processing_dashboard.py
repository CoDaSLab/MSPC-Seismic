import streamlit as st
from datetime import datetime, time
import mpld3
import streamlit.components.v1 as components
import scipy

# Make the directory jgarcia
import os
if os.getcwd() == "/home/jgarcia/digivolcan":
    os.chdir("..")


import sys
sys.path.append("digivolcan/functions")

from digivolcan.functions.SISMO import SISMO
from digivolcan.functions.HDAS import HDAS
from digivolcan.functions.data_check import get_filenames

# --- Defining Functions ---

def select_sensor(key):
    col = st.columns(2)
    sensor = col[0].selectbox('Sensor', ['PPMA', 'PLPI'], key=f"sensor_{key}")
    channel = col[1].selectbox('Channel', ['HHE', 'HHN', 'HHZ'], key=f"channel_{key}")

    return sensor, channel

def select_time(key):
    col = st.columns(2)
    start_date = col[0].date_input("Select a start day", key=f'start_date_{key}',
                                   value=datetime(2021, 9, 19))
    start_time = col[1].time_input("Select a start time", key=f'start_time_{key}',
                                 value = time(0,0,0))
    starttime = datetime.combine(start_date, start_time)

    end_date = col[0].date_input("Select an end day", key=f'end_date_{key}',
                                value=datetime(2021, 9, 20))
    end_time = col[1].time_input("Select an end time", key=f'end_time_{key}', 
                                 value = time(0,0,0))
    endtime = datetime.combine(end_date, end_time)

    return starttime, endtime

def select_detrend(key):
    detrend_options = [None, 'simple', 'linear', 'constant']
    detrend = st.selectbox('Detrend method', detrend_options, key=f"detrend_{key}",
                           disabled=True)
    return detrend

def select_interpolate(key):
    interpolate = st.checkbox('Interpolate', False,
                help="Interpolate missing measurements",
                key = f"interpolate_{key}")
    return interpolate


def select_windowing(key):
    windowing_options =  scipy.signal.windows.__all__ 
    if None not in windowing_options:
        windowing_options.append(None)
    windowing = col[0].selectbox('Windowing:', windowing_options, 10)
    if windowing != None:
        windowing = scipy.signal.windows.__dict__[windowing]

    return windowing


def set_yaxis(key):
    col = st.columns(2)
    set_yaxis = col[0].checkbox('Set Y axis', False, key=f"Y axis_{key}")
    col = st.columns(2)
    if set_yaxis:
        ylim_min = col[0].number_input('Y axis range:', value = -8e6)
        ylim_max = col[1].number_input('', value = +8e6)
        ylim = [ylim_min, ylim_max]
    else: ylim = None

    return ylim


def plot_seismogram(S, ylim, interactive):
        fig = S.plot_seismogram('', ylim, save=False)

        if interactive:
            with COL[1]:
                fig_html = mpld3.fig_to_html(fig)
                components.html(fig_html, height=600)
        else:
            COL[1].pyplot(fig)

# -------------------------
# --- Application start ---
# -------------------------

st.set_page_config(
    page_title= "SISMO Processing",
    layout='wide',
    page_icon='📉',
    )
st.title('SISMO Signal Processing')

tab_names = ["SISMO Trend", "SISMO FFT"]

tabs = st.tabs(tab_names)

# ------------ SISMO Trace ------------
with tabs[0]:
    key = 'Trend'
    COL = st.columns(2)
    loading_space = COL[1].empty()

    with COL[0]:
        st.subheader('Data selection')
        sensor, channel = select_sensor(key)
        starttime, endtime = select_time(key)

        st.subheader('Pre-processing')
        col = COL[0].columns(2)
        with col[0]:
            detrend = select_detrend(key)
        with col[1]:
            interpolate = select_interpolate(key)

        st.subheader('Trend plot')
        ylim = set_yaxis(key)
        col = COL[0].columns(2)
        with col[0]:
            interactive = st.checkbox('Interactive plot (Breaks x ticks)', False,
                            help="This feature is only available for short time periods")
        with col[1]:
            plot_trend = st.button('Plot trend')

    # Plotting area
    if plot_trend:
        with loading_space, st.spinner('Creating object'):
            # S  = create_object(starttime, endtime, detrend, interpolate)
            S = SISMO(sensor, channel, starttime, endtime,
                 interpolate = interpolate, detrend=detrend,
                 verbose=False)

        with loading_space, st.spinner('Plotting trace'):
            plot_seismogram(S, ylim, interactive)

# ------------ SISMO FFT ------------
with tabs[1]:
    key = 'FFT'
    COL = st.columns(2)
    loading_space = COL[1].empty()
    
    with COL[0]:
        st.subheader('Data selection')
        sensor, channel = select_sensor(key)
        starttime, endtime = select_time(key)

        st.subheader('Pre-processing')
        col = COL[0].columns(2)
        with col[0]:
            detrend = select_detrend(key)
        with col[1]:
            interpolate = select_interpolate(key)

        st.subheader('FFT parameters')
        col = COL[0].columns(2) 
        window_size = col[0].number_input('Window length in seconds', value = 3600.0)
        window_shift = col[1].number_input('Window overlap in seconds', value = 0.0)

        # Windowing
        windowing = select_windowing(key)
        FFT_points = col[1].number_input('Number of frequencies for the FFT', value = int(window_size*100),
                                         disabled=False)
        # FFT_points = int(100*window_size)

        
        

        st.subheader('FFT plot')
        col = COL[0].columns(2)
        ylim = set_yaxis(key)
        window_id = col[1].number_input('Window id for FFT:', min_value=0)
        with col[0]:
            interactive = st.checkbox('Interactive plot (Breaks x ticks)', False,
                            help="This feature is only available for short time periods",
                            key=f"Interactive_{key}")
        with col[1]:
            plot_fft = col[1].button('Plot FFT')

    if plot_fft:
        start_day = starttime.replace(hour=0, minute=0, second=0)
        filepaths, _,_ = get_filenames(start_day, endtime, sensor, channel)

        with loading_space, st.spinner('Creating object'):
            S = SISMO(sensor, channel, starttime, endtime,
                      interpolate = interpolate, windowing=None,
                      detrend=None,
                      verbose=True)
            # S.cutT(starttime, endtime)
            S.set_windows(window_size, window_size-window_shift)
            S.fft_bin(FFT_points)
        # """
        with loading_space, st.spinner('Plotting FFTs'):
            fig = S.plot_fft(window_id, '', ylim, save=False)

        if interactive:
            with COL[1]:
                fig_html = mpld3.fig_to_html(fig)
                components.html(fig_html, height=600)
        else:
            COL[1].pyplot(fig)
        # """



        with COL[1]:
            E_t, E_f = S.energy_check()

            st.write(f"\nEnergía en el dominio del tiempo:       {E_t}")
            st.write(f"Energía en el dominio de la frecuencia: {E_f}")
            st.write(f"division:                         {E_f/E_t}")




