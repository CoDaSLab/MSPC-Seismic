from config import *

from widgets.forms import *
from preprocessing.functions.feature_extraction import *

import pandas as pd

# --- Application start ---
init_page("Feature extraction")
init_session_state()
# ------------------------

tabs = st.tabs(['Feature Log', 'Extract new features'])

with tabs[0]:
    log = pd.read_csv("data/metadata/feature_log.csv",)
    st.dataframe(log)

with tabs[1]:
    key = 'extraction'
    COL = st.columns(2)
    with COL[0]:
        st.subheader("Sensor and time period")
        with st.expander("", expanded=True, ):
            sensors, channels = multi_select_sensor(key)
            starttime, endtime = select_time(key)

        st.subheader("Extraction parameters")
        window, overlap = select_window(key)

        col = COL[0].columns(2)
        with col[0]:
            windowing = select_windowing(key)
        with col[1]:
            FFT_points = select_FFT_points(key, window,)
        st.subheader("Features to extract:")
        col = COL[0].columns(2)
        types = []
        with col[0]:
            get_FFTs = st.checkbox('FFTs', True)
            if get_FFTs: types.append('FFT')
        with col[1]:
            get_feature_set = st.checkbox('feature set', disabled=True)
            if get_feature_set: types.append('feature')
        
        resampling_factor = st.number_input('Resampling factor (Temporary)', value=100)



    with COL[1]:

        extract_features = st.button('Extract Features', use_container_width=True)
        log_list = []
        if extract_features:
            for sensor in sensors:
                for channel in channels:
                    for type in types:
                        query = {
                            'sensor': sensor,
                            'channel': channel,
                            'type': type,
                            'starttime': starttime, 
                            'endtime': endtime,
                            'window': window,
                            'overlap': overlap,
                            'windowing': windowing,
                            'n_variables': int(FFT_points/2/resampling_factor*3),
                            'channel': channel,
                            }
                    log = check_log(query)
                    log_list.append(log)
                
                log = pd.concat(log_list)

            if len(log) > 0:
                st.warning("""
                            Some of the features you are trying to calculate have already been calulated.
                            \nYou can download them using the button below:
                            """)
                st.write("Calculated features with the same parameters:")
                st.write(log)

                # ids = log['file_id']
                # for id in ids:
                #     file = scipy.io.loadmat(f"data/metadata/features/{id}.mat")
                #     print(file)
                #     st.download_button(f"Download features [{id}.mat]",
                #                         file, f"{id}.mat", use_container_width=True)
            else:
                
                total_loops = len(sensors)*len(channels)*len(types) 
                current_loop = 1
                my_bar = st.progress(0, text = 'Total progress:')
                for sensor in sensors:
                    for channel in channels:
                        for type in types:
                           with st.spinner(f'[{current_loop}/{total_loops}] Creating object for sensor {sensor} and channel {channel}'):
                            S = SISMO(sensor, channel,
                                        starttime, endtime,
                                        False, # This is the detrend method,
                                        windowing,
                                        cpus = 10,)
                            S.resampling_factor = resampling_factor
                           with st.spinner(f'[{current_loop}/{total_loops}] Calculating {type}s for sensor {sensor} and channel {channel}'):
                            get_features(S, window, window-overlap, FFT_points,
                                    types,
                                    verbose = True, timer = True)

                            current_loop +=1
                            my_bar.progress( (current_loop-1)/total_loops, text='Total progress:')

                my_bar.empty()
                st.success('''The features have been extracted correctly.\n
                        You can now download them by selecting the same ones again''', icon="✔️", )
