import streamlit as st
from config.init import init_page, init_session_state
from utils.functions import get_stations

from widgets import *

from monitoring import utils
from datetime import datetime, timezone, timedelta
import pickle
import time
import numpy as np

# --- Application start ---
init_page("Real-time monitoring")
init_session_state()
st.title("Real-time monitoring")
# ------------------------
key="monitoring_rt"
forms.select_group(key)

st.subheader("Visualization")

# Configuration file
config = st.session_state.config
group = st.session_state.group

update_freq = timedelta(minutes=config["monitoring"]["update_frequency"])

starttime, endtime = utils.start_and_end_times(datetime.now(timezone.utc), 
                                        update_frequency=config["monitoring"]["update_frequency"],
                                        delay = config["monitoring"]["delay"])

if "start_date" not in st.session_state:
    st.session_state.start_date = datetime.date(starttime)
    st.session_state.start_time = datetime.time(starttime)
    st.session_state.end_date = datetime.date(endtime)
    st.session_state.end_time = datetime.time(endtime)

# Define fragments
@st.fragment(run_every=update_freq)
def real_time_visualization(config, nocs, key):
    exploration_on = False
    with st.form(key):
        col = st.columns(3)
        with col[0]:
            st.markdown("Time range for graphs:", help="Select a duration to view data from that many hours and minutes ago until now.")
            plot_time = forms.select_time_rt("plot_time_selector")
        
        with col[1]:
            n_consecutive_rt = st.number_input("Number of minimum consecutive windows over threshold", min_value=1, value=3,
                                        key = key + "consecutive_windows", 
                                        help="When the number of consecutive windows over the threshold is greater or equal than this number, " \
                                        "the corresponding windows will be colored red in the graph.")
            logscale_rt = st.checkbox("Log scale", value=True, key=key + "logscale",
                                        help="Display Y-axis using a logarithmic scale.")

        with col[2]:
            weight_rt = st.slider("T-score weight", 0.0, 1.0, value=0.5, step=0.05)
            refresh = st.form_submit_button("Refresh", type='primary', use_container_width=True)
    
    if refresh:
        st.cache_resource.clear()

    # Arrange graphs (2 per row)
    col1, col2 = st.columns(2) 
    exploration_on, starttime, endtime = False, None, None
    for i, noc in enumerate(nocs):
        if type(noc[1])==list:
            with col1:
                with st.spinner("Loading graph..."):
                    graph_attempt = 0
                    while graph_attempt < 3:
                        try:
                            selected_points = plots.plot_tscore_rt(noc[0], time_range=plot_time, T_weight=weight_rt, logscale=logscale_rt, 
                                n_consecutive=n_consecutive_rt)
                            other.noc_summary(noc[0])
                            st.session_state.rt_stations = noc[1]
                            break
                        except pickle.UnpicklingError:
                            time.sleep(5)
                            graph_attempt += 1
                    else:
                        st.error(f"Failed to load graph for NOC {noc[0]}.")
                        
            try:
                with col2:
                    if selected_points["selection"]["points"]:
                        st.subheader("oMEDA")
                        from monitoring.NOC import NOC
                        nocs_path = config["paths"]["nocs"]
                        omeda_noc = NOC.load(f"{nocs_path}/{noc[0]}")

                        n_components = None

                        omeda_options =  ["PCA model", "Residuals", "All"]
                        omeda_opt = st.segmented_control("Compare data by:", omeda_options, selection_mode='single', 
                                                            default = omeda_options[1], key = key + 'component_omeda')

                        if omeda_opt == omeda_options[0]:
                            n_components = omeda_noc.n_components
                        elif omeda_opt == omeda_options[1]:
                            n_components = np.arange(omeda_noc.n_components + 1, omeda_noc.features_shape[1] + 1)
                        elif omeda_opt == omeda_options[2]:
                            n_components = omeda_noc.features_shape[1]
                        else:
                            st.error("Please select an option.")
                        
                        if n_components is not None:
                            exploration_on = True
                            omeda_stations = omeda_noc.station
                            starttime = selected_points["selection"]["points"][0]["x"]
                            endtime = selected_points["selection"]["points"][-1]["x"]
                            try:
                                starttime = datetime.strptime(starttime, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                            except: starttime = datetime.strptime(starttime, "%Y-%m-%d %H:%M").strftime("%Y-%m-%d %H:%M:%S")
                            try:
                                endtime = datetime.strptime(endtime, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                            except: endtime = datetime.strptime(endtime, "%Y-%m-%d %H:%M").strftime("%Y-%m-%d %H:%M:%S")
                            with st.spinner("Calculating oMEDA..."):
                                omeda_vec, freqs_label, channel_class, stations_class = omeda_noc.omeda(starttime, endtime, n_components)
                                fig = plots.plot_omeda(omeda_vec, stations_class, channel_class, freqs_label, logscale=False)

                        st.plotly_chart(fig, use_container_width=True)
            except Exception as e: 
                col2.error(f"Error computing oMEDA. {e}")
        
            if exploration_on:
                other.exploration(starttime, endtime, omeda_stations, key=key+f"_exploration_{group["name"]}")

        # if i%2==0:
        #     with col1:
        #         with st.spinner("Loading graph..."):
        #             graph_attempt = 0
        #             while graph_attempt < 3:
        #                 try:
        #                     plots.plot_tscore_rt(noc[0], time_range=plot_time, T_weight=weight_rt, logscale=logscale_rt, 
        #                         n_consecutive=n_consecutive_rt, nocs_path=config["paths"]["nocs"])
        #                     other.noc_summary(noc[0], config["paths"]["nocs"])
        #                     break
        #                 except pickle.UnpicklingError:
        #                     time.sleep(5)
        #                     graph_attempt += 1
        #             else:
        #                 st.error(f"Failed to load graph for NOC {noc[0]}.")
        # else:
        #     # Right column
        #     with col2:
        #         with st.spinner("Loading graph..."):
        #             graph_attempt = 0
        #             while graph_attempt < 3:
        #                 try:
        #                     plots.plot_tscore_rt(noc[0], time_range=plot_time, T_weight=weight_rt, logscale=logscale_rt, 
        #                         n_consecutive=n_consecutive_rt, nocs_path=config["paths"]["nocs"])
        #                     other.noc_summary(noc[0], config["paths"]["nocs"])
        #                     break
        #                 except pickle.UnpicklingError:
        #                     time.sleep(5)
        #                     graph_attempt += 1
        #             else:
        #                 st.error(f"Failed to load graph for NOC {noc[0]}.")
    
    return starttime, endtime


# ---------- Real-time Visualization ----------

if config["monitoring"]["auto_monitoring"]:
    try:
        avail_data = utils.get_available_stations(config["paths"]["latest_pulls_log"], tolerance=2 * config["monitoring"]["update_frequency"])
        avail_stations = [x[1] for x in avail_data if x[1] in get_stations(group["name"])]
    except FileNotFoundError as e:
        st.error(f"Latest data downloads log not available. More details:\n{e}")
    try:
        nocs = utils.check_nocs(config["paths"]["noc_log"], group["stations"])
        starttime, endtime = real_time_visualization(config, nocs=nocs, key=key)

    except FileNotFoundError as e:
        st.error(f"NOC list not available. More details:\n{e}")
else:
    st.error('Real-time monitoring is disabled. Enable it on the "Configuration" page.')