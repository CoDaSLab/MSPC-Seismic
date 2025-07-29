from config import *
from widgets.forms import select_time
from widgets import maps
from widgets.tables import available_stations

from utils.functions import load_events

# --- Application start ---
init_page("Location Map")
init_session_state()
st.title('Data mapping')
# ------------------------

events = load_events()

COL = st.columns(2)
with COL[0]:
    # display station table
    with st.expander("Available stations"):#, help = "Source: INVOLCÁN"):
        stations = available_stations()

with COL[1]:
    col = st.columns(2)
    # Display Volcano Peak ?
    with col[0]:
        display_peak = st.checkbox("Display Tajogaite Peak", True)

    # Display stations ?
    with col[1]:
        display_available_stations = st.checkbox('Display available stations', value = True)
        display_all_stations = st.checkbox('Display all stations', value = False)
        stations = maps.choose_stations(stations, display_available_stations, display_all_stations)

    # Display events ?
    with col[0]:
        display_events = st.checkbox("Display events", False)

    event_color, starttime, endtime = '', 0, 0
    if display_events:
        starttime, endtime = select_time('map')
        event_color = st.selectbox("Color based on:", ['time', 'magnitude', 'depth'], index=1)
    events_map = maps.choose_events(events, display_events, starttime, endtime)


    # Show map
    maps.show_map(display_peak, stations, events_map, event_color)

with COL[0]:
    # display events table
    if len(events_map) == 0:
        st.dataframe(events, use_container_width = True)
    else: 
        st.dataframe(events_map, use_container_width = True)
    st.write("Source: INVOLCÁN")
    # with st.expander('Stats:'):
    #     st.write(events.describe())
