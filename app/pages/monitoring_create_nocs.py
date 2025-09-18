import streamlit as st
from config.init import init_page, init_session_state
from config.interface import header_monitoring

from widgets import *
from utils import functions

import numpy as np
import pandas as pd
import os

from preprocessing.fft_rt import calculate_fft_rt
from monitoring import NOC

# --- Application start ---
init_page("Monitoring - NOC creator")
init_session_state()
st.title("Monitoring")
header_monitoring()
# ------------------------

st.subheader("NOC creator")

config = st.session_state.config

key = 'noc_maker'
COL = st.columns(2)
with COL[0]:
    with st.form(key):
        st.subheader("Station and time period:")
        starttime, endtime = forms.select_time(key)
        starttime = pd.Timestamp(starttime, tz='UTC')
        endtime = pd.Timestamp(endtime, tz='UTC')
        
        network = config["data"]["network"]
        station, channels = forms.select_station_multi_channel(key, station_list=config["data"]["stations"], 
                                                                channel_list=config["data"]["channels"])

        st.subheader("Extraction parameters:")
        window, shift = forms.select_window(key)

        col = st.columns(2)
        with col[0]:
            detrend = forms.select_detrend(key)
            windowing = forms.select_windowing(key)
        with col[1]:
            fft_auto = st.checkbox("Set FFT points automatically", value=True)
            fft_points = forms.select_FFT_points(key, window)
            if fft_auto:
                fft_points = 'auto'

        st.subheader("Features to extract:")
        feature_options = ["spectrogram_unfold"]
        feature_types = st.multiselect("Select feature types", options=feature_options, default=feature_options[0],
                                        help="Available feature types are FFT coefficients and derivatives.")
        
        # NOC parameters
        st.subheader("NOC parameters:")
        col = st.columns(2)
        with col[0]:
            noc_name = st.text_input("NOC name", help="The end date will be automatically appended to the name.")
            noc_type = st.selectbox("NOC type", options=["dynamic", "static", "inactive", "unavailable"],
                                    help="- dynamic: updates automatically\n- static: does not update automatically\n" \
                                    "- inactive: is not used for real-time monitoring\n- unavailable: makes it invisible to the app")
        with col[1]:
            prep = forms.select_preprocessing(key)
            quantile = st.number_input("Quantile", min_value=0.0, value=0.99, max_value=1.0,
                                        help="Quantile to be used as threshold for anomaly detection.")
        
        submit = st.form_submit_button("Create NOC", use_container_width=True, type="primary")

    if submit:
        with st.spinner("Calculating features..."):
            features = calculate_fft_rt(starttime, endtime, network=network, stations=station, 
                                        channels=channels, window_length=window,
                                        window_shift=shift, detrend=detrend,
                                        windowing=windowing, n_bins=fft_points, 
                                        merge_method=config["features"]["merge_method"], merge_fill_value=config["features"]["merge_fill_value"],
                                        pad_fill_value=config["features"]["pad_fill_value"], data_path=config["paths"]["data"], 
                                        cpus=config["features"]["cpus"], verbose=False, save=False)
            
            train_data = np.hstack([features[k] for k in feature_types])
        
        with st.spinner("Creating NOC..."):
            if noc_name == "":
                noc_name = station + '_' + noc_type[0]
            noc_name = noc_name + '_' + endtime.strftime("%Y-%m-%d")
            st.session_state.noc_name = noc_name
            noc = NOC.NOC(noc_name, train_data, features["times_label"], network=network, station=station,
                            type=noc_type, preprocessing=prep, n_components=1, percentile_threshold=True,
                            quantile_threshold=quantile, csv_path=config["paths"]["noc_log"])
            
        with st.spinner("Saving NOC..."):
            noc.save(os.path.join(config["paths"]["nocs"], noc_name).replace('\\', '/'))
            noc.write_csv()
        
        st.success("NOC created successfully. Select the number of principal components to complete the NOC's configuration.",
                    icon="✔️")

with COL[1]:
    # Visualize explained variance by number of components
    with st.expander("Explained variance by number of components", expanded=submit):
        if submit:
            with st.spinner("Calculating..."):
                plots.plot_var_pca(noc.features, preprocessing=prep)
        else:
            st.write("Create a NOC first.")   

    with st.form(key + "_pca"):
        st.subheader("Select a number of principal components:", help="You need to create a NOC first.")
        col = st.columns(2)
        with col[0]:
            n_components = st.number_input("Number of components", min_value=1, value='min')
        with col[1]:
            submit_dq = st.form_submit_button("Set number of components", disabled=not submit,
                                            type="primary", use_container_width=True)
                
    if submit_dq:
        with st.spinner("Configuring NOC..."):
            # Update NOC
            noc = NOC.NOC.load(os.path.join(config["paths"]["nocs"], st.session_state.noc_name))
            noc.n_components = n_components
            noc.update()
        
        with st.spinner("Saving changes..."):
            noc.save(os.path.join(config["paths"]["nocs"], st.session_state.noc_name).replace('\\', '/'))
            noc.write_csv()
        
        st.success("NOC configured successfully.", icon="✔️")

with st.expander("NOC list"):
    data = functions.load_data(config["paths"]["noc_log"])
    data = tables.filter_dataframe(data)
    tables.show_table(data)
