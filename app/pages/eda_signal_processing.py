from config import *

from widgets.forms import *
from widgets.plots import *
from preprocessing.SISMO import SISMO
from utils.functions import read_streams, load_files
import pandas as pd

# -------------------------
# --- Application start ---
# -------------------------
init_page("EDA - Signal visualization")
init_session_state()
st.title('Exploratory Data Analysis (EDA)')
header_eda()
# -------------------------

st.subheader("Signal visualization")

tab_names = ["SISMO Trend", "SISMO FFT"]
tabs = st.tabs(tab_names)

config = st.session_state.config

# ------------ SISMO Trace ------------
with tabs[0]:
    key = 'Trend'
    COL = st.columns(2)
    loading_space = COL[1].empty()

    with COL[0]:
        starttime, endtime = select_time('time_selector_exploration')
        starttime = pd.Timestamp(starttime, tz='UTC')
        endtime = pd.Timestamp(endtime, tz='UTC')

        station_list = config["data"]["stations"]
        network = config["data"]["network"]

        st.subheader('Data selection')
        station, channels = select_station_multi_channel(key, station_list, ['HHE', 'HHN', 'HHZ'])
        # starttime, endtime = select_time(key)

        st.subheader('Pre-processing')
        col = COL[0].columns(2)
        with col[0]:
            detrend = select_detrend(key)

        st.subheader('Trend plot')
        ylim = set_yaxis(key)
        col = COL[0].columns(2)
        with col[0]:
            interactive = st.checkbox('Interactive plot (Breaks x ticks)', False,
                            help="This feature is only available for short time periods")
        with col[1]:
            plot_trend = st.button('Plot trend', use_container_width=True, type="primary")

    # Plotting area
    if plot_trend:
        col = st.columns(2)
        with loading_space, st.spinner('Creating object'):
            sismos = []
            for channel in channels:
                S = SISMO(network, station, channel, starttime, endtime,
                        detrend=detrend, windowing=None, merge_method=0,
                        cpus=1, data_path=config["paths"]["data"],
                        verbose = False)
                sismos.append(S)

        with loading_space, st.spinner('Plotting trace'):
            with COL[1]:
                for i in range(len(channels)):
                    plot_seismogram(sismos[i], ylim, interactive)





# ------------ SISMO FFT ------------
with tabs[1]:
        
    key = 'FFT'
    COL = st.columns(2)
    loading_space = COL[1].empty()
    
    with COL[0]:
        starttime, endtime = select_time('time_selector_fft')
        starttime = pd.Timestamp(starttime, tz='UTC')
        endtime = pd.Timestamp(endtime, tz='UTC')

        station_list = config["data"]["stations"]
        network = config["data"]['network']

        st.subheader('Data selection')
        station, channel = select_station(key, station_list)

        st.subheader('Pre-processing')
        col = COL[0].columns(2)
        with col[0]:
            detrend = select_detrend(key)

        st.subheader('FFT parameters')
        window_size, window_shift = select_window('FFT')

        # Windowing
        col = COL[0].columns(2) 
        with col[0]:
            windowing = select_windowing(key)
        with col[1]:
            FFT_points = select_FFT_points('FFT', window_size)

        st.subheader('FFT plot')
        col = COL[0].columns(2)
        ylim = set_yaxis(key)
        window_id = col[1].number_input('Window id for FFT:', min_value=0)
        with col[0]:
            interactive = st.checkbox('Interactive plot (Breaks x ticks)', False,
                            help="This feature is only available for short time periods",
                            key=f"Interactive_{key}")
        with col[1]:
            plot_freq = col[1].button('Plot FFT', use_container_width=True, type='primary')

    if plot_freq:
        with loading_space, st.spinner('Creating object'):  
            S = SISMO(network, station, channel, starttime, endtime,
                        detrend=detrend, windowing=windowing, merge_method=0,
                        cpus=1, data_path=config["paths"]["data"],
                        verbose = False)

        with loading_space, st.spinner('Calculating FFTs'):
            S.set_windows(window_size, window_shift)
            S.fft_bin(FFT_points)
        with loading_space, st.spinner('Plotting trace'):
            with COL[1]:
                plot_fft(S, window_id, ylim, interactive)

