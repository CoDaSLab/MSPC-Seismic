from config import *
from widgets.forms import select_time
from widgets import maps
from widgets.tables import available_sensors

from utils.functions import load_events, load_sensors

# --- Application start ---
init_page("Location Map")
init_session_state()
# st.title('Data mapping')
# ------------------------

import folium
from streamlit_folium import st_folium 


# ------------------------
# Read station data
sensors = load_sensors()


st.markdown("Select your area of interest:")
col  = st.columns(2)
with col[0]:

    m,output = maps.draw_map(st.session_state.map)
    st.session_state.map = m

    drawings = output["all_drawings"]
    sensors = maps.sensor_selector(drawings, sensors)

    if sensors is not None and len(sensors)>1:
        st.session_state.sensors = sensors
        import copy
        disp_map = copy.deepcopy(m)
        for i in range(len(sensors)):
            folium.Marker(
            location=[sensors.iloc[i]['lat'], sensors.iloc[i]['lon']],
            popup=sensors.iloc[i]['station'],
            ).add_to(disp_map)

with col[1]:
        if sensors is not None and len(sensors)>1:
            maps.show_map(disp_map)
            st.markdown("Sensors in area:")
            st.dataframe(st.session_state.sensors)
            # st.rerun()
        submit = st.button("Keep sensor selection", use_container_width=True)
        if submit:
            sensors = st.session_state.sensors

