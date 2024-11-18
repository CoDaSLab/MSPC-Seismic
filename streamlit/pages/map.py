import streamlit as st
from streamlit_utils.interface import header, logo
from streamlit_utils.widgets import select_time
from streamlit_utils.utils import init_session_state

import pandas as pd
import folium
from streamlit_folium import st_folium 
from matplotlib import cm, colors
import branca.colormap as bcm


def plot_folium_points(map, data):
    if not data.empty:
        fill = 'magnitude' in data # Only event points are filled
        for _, row in data.iterrows():
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=5,
                color= row['color'],
                fill=fill,
                fill_opacity=0.9,
                popup=get_popup(row)
            ).add_to(map)

    return map

def get_popup(row):
    if 'magnitude' in row:
        html = f"""
        <center>
        <p style="font-family: sans-serif">
            lat: {row['latitude']}º<br>
            lon: {row['longitude']}º<br>
            mag: {row['magnitude']}<br><br>
            datetime: {row['datetime']}"""
        iframe = folium.IFrame(html, width=150, height=150)
        
    elif 'sensor' in row:
        html = f"""
        <center>
        <p style="font-family: sans-serif">
            sensor: {row['sensor']}<br>
            lat: {row['latitude']}º<br>
            lon: {row['longitude']}º"""
        iframe = folium.IFrame(html, width=150, height=70)
          
    else:
        html = f"""
        <center>
        <p style="font-family: sans-serif">
            lat: {row['latitude']}º<br>
            lon: {row['longitude']}º"""
        iframe = folium.IFrame(html, width=150, height=50)

    return folium.Popup(iframe, max_width=500)

# -- Define colors for markers --
colormap = colors.LinearSegmentedColormap.from_list("yellow_to_red", ["#55ff00", "#fff700", "#FF0000"])
colormap.set_extremes = [0, 0, 1]
marker_colors = {
    'sensors': '#1bffe3', # Cyan
    'Volcano peak': '#000000', # black
    'missing_magnitude': "#b2b2b2",
    'magnitudes': colormap,
    'time': colormap
}

# --- Application start ---
st.set_page_config(
    page_title= "Location Map",
    layout='wide',
    page_icon='🗺️',
    )
init_session_state()
logo()
header()
# ------------------------


st.title('Data mapping')

# Load sensor location data
column_names = ["sensor", "latitude", "longitude", "altitude (m)"]
sensors = pd.read_csv("digivolcan/database/stations_lp.dat", sep="\s+", names=column_names)
sensors['available'] = False
sensors.loc[sensors['sensor'].isin(['PPMA', 'PLPI']), 'available'] = True
sensors = sensors.sort_values('available', ignore_index=True, ascending=False)

# Load registered events data
events = pd.read_csv("digivolcan/database/ivc_available_data.csv",
    usecols = ['year', 'month', 'day', 'hour', 'minute', 'second', 'magnitude', 'longitude', 'latitude'])

# Order by date and time
events = events.sort_values(by=[events.columns[0], events.columns[1], events.columns[2],
                            events.columns[3], events.columns[4], events.columns[5], 
                            ]) .reset_index(drop=True)

min_magnitude = events['magnitude'].min()
max_magnitude = events['magnitude'].max()

COL = st.columns(2)
with COL[1]:
    map_center = [28.612778, -17.866111] 
    folium_map = folium.Map(location=map_center, zoom_start=11,  tiles="CartoDB positron")

    col = st.columns(2)
    # Display Volcano Peak
    with col[0]:
        display_peak = st.checkbox("Display Tajogaite Peak", True)
        if display_peak:
            plot_peak = pd.DataFrame([[-17.866111, 28.612778, marker_colors['Volcano peak']]],
                                        columns = ['longitude', 'latitude', 'color'])
        else: plot_peak = pd.DataFrame([])

    # Display sensors
    with col[1]:
        display_available_sensors = st.checkbox('Display available sensors', value = True)
        display_all_sensors = st.checkbox('Display all sensors', value = False)

        plot_sensors = pd.DataFrame([])
        if display_all_sensors:
            plot_sensors = sensors
        elif display_available_sensors:
            plot_sensors = sensors[sensors['available']  == True]

        if len(plot_sensors)>0:
            plot_sensors['color'] = [marker_colors['sensors']] * len(plot_sensors)

# Display events
with COL[1]:

    display_events = st.checkbox("Display events", False)
    if display_events:
        plot_events = events
        starttime, endtime = select_time('map')
        plot_events['datetime'] = pd.to_datetime(events[['year', 'month', 'day', 'hour', 'minute', 'second']])
        plot_events = plot_events[(plot_events['datetime'] >= starttime) & (plot_events['datetime'] <= endtime)]

        event_color = st.selectbox("Color based on:", ['time', 'magnitude'], index=1)

        if event_color == 'time':
            min_time    = plot_events['datetime'].min()
            time_range  = ((plot_events['datetime'] - min_time).dt.seconds).to_numpy()
            time_portion = time_range/max(time_range)
            
            plot_events['color'] = [colors.rgb2hex(marker_colors['time'](x))
                                    for x in time_portion]
            # For colorbar
            min_value, max_value = time_range[0], time_range[-1]
            caption = 'Time'

        if event_color == 'magnitude':
            plot_events['color'] = plot_events['magnitude'].apply(
                lambda x: marker_colors['missing_magnitude'] if x == -1 
                    else colors.rgb2hex(marker_colors['magnitudes'](x / max_magnitude)))
        
            # For colorbar
            min_value, max_value = 0, max_magnitude
            caption = 'Magnitude'



        selected_events_ids = plot_events.index.to_list()
        events = events.iloc[selected_events_ids]
        events = events[events.columns.tolist()[:-1]]

                
    else: plot_events = pd.DataFrame([])

    # ---------------------------------


    if display_events:
        norm = colors.Normalize(vmin=min_value, vmax=max_value)
        color_scale = bcm.LinearColormap(
            colors=[colormap(i) for i in range(colormap.N)],
            vmin=min_value, vmax=max_value
        )
        color_scale.caption = caption
        color_scale.add_to(folium_map)


    folium_map = plot_folium_points(folium_map, plot_events)
    folium_map = plot_folium_points(folium_map, plot_peak)
    folium_map = plot_folium_points(folium_map, plot_sensors)

    st_folium(folium_map, use_container_width=True)


with COL[0]:

    # st.subheader("Available sensors", help = "Source: INVOLCÁN")
    with st.expander("Available sensors"):#, help = "Source: INVOLCÁN"):
        st.dataframe(sensors, use_container_width = True)
        st.write("Source: INVOLCÁN")

    st.subheader("Registered events", help = "Maximazing the table might cause the app to break if there are too many rows")
    st.dataframe(events.iloc[:], use_container_width = True)
    st.write("Source: INVOLCÁN")
    with st.expander('Stats:'):
        st.write(events.describe())
