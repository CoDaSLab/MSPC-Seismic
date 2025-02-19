import streamlit as st
import folium
from streamlit_folium import st_folium 
import branca.colormap as bcm
from matplotlib import cm, colors
import pandas as pd


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

def choose_sensors(sensors, display_available_sensors, display_all_sensors):
    plot_sensors = []
    if display_all_sensors:
        plot_sensors = sensors
    elif display_available_sensors:
        plot_sensors = sensors[sensors['available']  == True]

    if len(plot_sensors)>0:
        plot_sensors['color'] = [marker_colors['sensors']] * len(plot_sensors)

    return plot_sensors

def choose_events(events, display_events, starttime, endtime):
    if display_events:
        plot_events = events

        plot_events = plot_events[(plot_events['datetime'] >= starttime) & (plot_events['datetime'] <= endtime)]

        selected_events_ids = plot_events.index.to_list()
        events = events.iloc[selected_events_ids]
        events = events[events.columns.tolist()[:-1]]
                
    else: plot_events = []
    return plot_events

def show_map(peak, sensors, events, event_color, center = [28.612778, -17.866111] ):
    if peak:
        peak = [-17.866111, 28.612778] # Tajogaite Peak coordinates
        peak.append(marker_colors['Volcano peak'])
        peak = pd.DataFrame([peak], columns = ['longitude', 'latitude', 'color'])
    else: peak = pd.DataFrame([])

    sensors = pd.DataFrame(sensors)
    events = pd.DataFrame(events)
    if event_color == 'time':
        min_time    = events['datetime'].min()
        time_range  = ((events['datetime'] - min_time).dt.seconds).to_numpy()
        time_portion = time_range/max(time_range)
        
        events['color'] = [colors.rgb2hex(marker_colors['time'](x))
                                for x in time_portion]
        # For colorbar
        min_value, max_value = time_range[0], time_range[-1]
        caption = 'Time'

    if event_color == 'magnitude':
        max_mag = max(events['magnitude'])
        events['color'] = events['magnitude'].apply(
            lambda x: marker_colors['missing_magnitude'] if x == -1 
                else colors.rgb2hex(marker_colors['magnitudes'](x / max_mag)))
    
        # For colorbar
        min_value, max_value = 0, max_mag
        caption = 'Magnitude'

    if event_color == 'depth':
        max_depth = max(events['depth (km)'])
        events['color'] = events['depth (km)'].apply(
            lambda x: marker_colors['missing_magnitude'] if x == -1 
                else colors.rgb2hex(marker_colors['magnitudes'](x / max_depth)))
    
        # For colorbar
        min_value, max_value = 0, max_depth
        caption = 'Depth (km)'

    
    folium_map = folium.Map(location=center, zoom_start=11,  tiles="CartoDB positron")
    folium_map = plot_folium_points(folium_map, events)
    folium_map = plot_folium_points(folium_map, peak)
    folium_map = plot_folium_points(folium_map, sensors)

    if len(events) > 1:
        norm = colors.Normalize(vmin=min_value, vmax=max_value)
        color_scale = bcm.LinearColormap(
            colors=[colormap(i) for i in range(colormap.N)],
            vmin=min_value, vmax=max_value
        )
        color_scale.caption = caption
        color_scale.add_to(folium_map)

    st_folium(folium_map, use_container_width=True)

    return  

