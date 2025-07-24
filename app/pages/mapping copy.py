from config import *
from widgets.forms import select_time
from widgets import maps
from widgets.tables import available_sensors

from utils.functions import load_events

# --- Application start ---
init_page("Location Map")
init_session_state()
st.title('Data mapping')
# ------------------------

events = load_events()

COL = st.columns(2)
with COL[0]:
    # display sensor table
    with st.expander("Available sensors"):#, help = "Source: INVOLCÁN"):
        sensors = available_sensors()

with COL[1]:
    col = st.columns(2)
    # Display Volcano Peak ?
    with col[0]:
        display_peak = st.checkbox("Display Tajogaite Peak", True)

    # Display sensors ?
    with col[1]:
        display_available_sensors = st.checkbox('Display available sensors', value = True)
        display_all_sensors = st.checkbox('Display all sensors', value = False)
        sensors = maps.choose_sensors(sensors, display_available_sensors, display_all_sensors)

    # Display events ?
    with col[0]:
        display_events = st.checkbox("Display events", False)

    event_color, starttime, endtime = '', 0, 0
    if display_events:
        starttime, endtime = select_time('map')
        event_color = st.selectbox("Color based on:", ['time', 'magnitude', 'depth'], index=1)
    events_map = maps.choose_events(events, display_events, starttime, endtime)


    # Show map
    maps.show_map(display_peak, sensors, events_map, event_color)

with COL[0]:
    # display events table
    if len(events_map) == 0:
        st.dataframe(events, use_container_width = True)
    else: 
        st.dataframe(events_map, use_container_width = True)
    st.write("Source: INVOLCÁN")
    # with st.expander('Stats:'):
    #     st.write(events.describe())
