from config import *
from widgets.forms import select_time
from widgets import maps
from widgets.tables import available_stations

from utils.functions import load_events, load_stations, load_files, read_streams

# --- Application start ---
init_page("Location Map")
init_session_state()
# st.title('Data mapping')
# ------------------------

import folium
from streamlit_folium import st_folium 
import copy

if "submitted_map" not in st.session_state: st.session_state.submitted_map = False
submitted_map = st.session_state.submitted_map
if "submitted_time" not in st.session_state: st.session_state.submitted_time = False
submitted_time = st.session_state.submitted_time
if "submitted_selection" not in st.session_state: st.session_state.submitted_selection = False
submitted_selection = st.session_state.submitted_selection
if "ST" not in st.session_state: st.session_state.ST = None
# ------------------------
# Read station data
stations = load_stations()


COL  = st.columns(2)
# COL[0].markdown("Select your area of interest:")
col  = st.columns(2)

if submitted_map and not submitted_selection:
    with col[0]:
        marked_map = st.session_state.marked_map
        stations = st.session_state.stations
        maps.draw_map(marked_map)

if not submitted_map:
    with col[0]:
        m,output = maps.draw_map(st.session_state.map)
        st.session_state.map = m
            
        drawings = output["all_drawings"]   
        stations = maps.station_selector(drawings, stations)

        if stations is not None:
            marked_map = maps.add_stations(st.session_state.map, stations)


    with col[1]:
            if not submitted_map:
                if stations is not None and len(stations)>1:
                    maps.show_map(marked_map)
                    st.markdown("Stations in area:")
                    st.dataframe(stations)
                    # st.rerun()
    with COL[1]:
            if not submitted_map:
                submit = st.button("Keep station selection", use_container_width=True, disabled = (drawings is None))
                if submit:
                    st.session_state.stations = stations
                    st.session_state.marked_map = marked_map
                    st.session_state.submitted_map = True
                    st.rerun()



## Select the time range

if submitted_map and not submitted_time and not submitted_selection:


    with col[1]:
        import pandas as pd
        starttime, endtime = select_time('time_selector_exploration')
        starttime = pd.Timestamp(starttime, tz='UTC')
        endtime = pd.Timestamp(endtime, tz='UTC')


        files = load_files()
        files['start_time'] = pd.to_datetime(files['start_time'], utc=True)
        files['end_time'] = pd.to_datetime(files['end_time'], utc=True)


        eruption_files = files[(files['start_time']==starttime) | (files['end_time']==endtime) ]
        eruption_stations = pd.unique(eruption_files['station']).tolist()

        stations = st.session_state.stations
        stations=stations[stations['station'].isin(eruption_stations)]

        marked_map = maps.add_stations(st.session_state.map, stations)
        maps.show_map(marked_map)
        st.dataframe(stations)


    with COL[1]:
        if not submitted_time:
            submit = st.button("Keep time range selection", use_container_width=True)
            if submit:
                st.session_state.stations = stations
                st.session_state.starttime = starttime
                st.session_state.endtime = endtime
                st.session_state.marked_map = marked_map
                st.session_state.submitted_time = True
                st.rerun()

if submitted_time and not submitted_selection:
    with col[1]:
        stations = st.session_state.stations
        stations = st.data_editor(stations)
        stations.dropna(inplace=True)
        
        starttime, endtime = select_time("confirm")

        submit = st.button("Confirm selection", use_container_width=True)
        if submit:
            st.session_state.stations = stations
            st.session_state.starttime = starttime
            st.session_state.endtime = endtime
            st.session_state.marked_map = marked_map
            st.session_state.submitted_selection = True
            st.session_state.ST = None
            st.rerun()

# -----------------------------------
from folium.plugins import Fullscreen
if submitted_selection:

    tajogaite_lat = 28.612778
    tajogaite_lon = -17.866111

    stations = st.session_state.stations
    marked_map = maps.add_stations(st.session_state.map, stations)
    Fullscreen(position="topleft").add_to(marked_map)
    
    folium.Marker(
    location=[tajogaite_lat, tajogaite_lon],
    popup="Tajogaite Peak", # Text that appears when you click the marker
    tooltip="Tajogaite Peak", # Text that appears when you hover over the marker
    icon=folium.Icon(color='red', icon='fire', prefix='fa') # Optional: Customize the icon
    ).add_to(marked_map)

    maps.show_map(marked_map)


# if submitted_selection:
#     # data_path = "data/involcan/mseed"
#     stations = st.session_state.stations['station'].to_list()
#     starttime = st.session_state.starttime
#     endtime = st.session_state.endtime
#     ST = st.session_state.ST

#     if st.session_state.ST == None:
#         ST = read_streams(stations, starttime, endtime)
#         st.session_state.ST = ST

#     if col[0].checkbox("Plot seismograms"):
#         with col[1].expander("Seismogram plots"):
#             for stream in ST:
#                 fig = stream.plot();
#                 st.pyplot(fig)



