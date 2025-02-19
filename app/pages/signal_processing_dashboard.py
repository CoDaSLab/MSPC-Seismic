from config import *

from widgets.forms import *
from widgets.plots import *
from preprocessing.functions.SISMO import SISMO

# -------------------------
# --- Application start ---
# -------------------------
init_page("SISMO visualization")
init_session_state()
st.title('SISMO Signal Processing')
# -------------------------




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
                    
            S = SISMO(sensor, channel, starttime, endtime,
                        detrend,
                        None, # windowing
                        2, # cpus
                        verbose = False)

        with loading_space, st.spinner('Plotting trace'):
            with COL[1]:
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
            plot_freq = col[1].button('Plot FFT')

    if plot_freq:
        with loading_space, st.spinner('Creating object'):  
            S = SISMO(sensor, channel, starttime, endtime,
                        detrend,
                        windowing,
                        2, # cpus
                        verbose=False)

        with loading_space, st.spinner('Calculating FFTs'):
            S.set_windows(window_size, window_size-window_shift)
            S.fft_bin(FFT_points)
        with loading_space, st.spinner('Plotting trace'):
            with COL[1]:
                plot_fft(S, window_id, ylim, interactive)






