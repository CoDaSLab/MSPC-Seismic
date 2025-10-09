from config import *
from widgets import maps
from utils.functions import load_last_pulls, load_stations

from datetime import datetime, timezone, timedelta
import pandas as pd
import os

# --- Application start ---
init_page("Digivolcan Home")
init_session_state()

st.markdown("---")
# st.markdown("<h1 style='text-align: center;'>Digivolcan Home</h1>", unsafe_allow_html=True)

# Station health check code
@st.fragment(run_every = timedelta(seconds=2))
def station_health_check():
    st.markdown("<h3 style='text-align: center;'>Running stations</h3>", unsafe_allow_html=True)
    last_pulls = load_last_pulls()
    stations = load_stations()

    if last_pulls is not None:
        now = st.session_state.now
        last_pulls["time_since_last_pull"] = now-last_pulls["latest_pull_time"]

        last_pulls = last_pulls[last_pulls["time_since_last_pull"] <= pd.Timedelta(days=30)]
        active_stations = last_pulls['station'].unique()

        active_stations_dic = {
            'station':[],
            'time_since_last_pull':[],
            'color':[],
            'popup':[],
        }

        for active_station in active_stations:
            station_rows = last_pulls[ last_pulls["station"] == active_station]    
            time = station_rows["time_since_last_pull"].max()

            if   time < pd.Timedelta(minutes=5): color = "green" 
            elif time < pd.Timedelta(minutes=10): color = "orange" 
            else: color = "red" 

            active_stations_dic['station'].append(active_station)
            active_stations_dic['time_since_last_pull'].append(time)
            active_stations_dic['color'].append(color)
            popup = "<br>Last updates:<br>"
            for _, row in station_rows.iterrows():
                td = row['time_since_last_pull']
                popup += f"{row['channel']}: {td.components.days:02d}d {td.components.hours:02d}h:{td.components.minutes:02d}m:{td.components.seconds:02d}s<br>"

            active_stations_dic['popup'].append(popup)


        # Display the Map
        map = maps.create_map()
        map = maps.add_stations(map, stations[stations['station'].isin(active_stations)],
                                color=active_stations_dic['color'],
                                popup=active_stations_dic['popup'])
        maps.show_map(map)

    return

def anomaly_log(head = None):
    anomaly_log_path = st.session_state.config["paths"]["anomaly_log"]
    if os.path.exists(anomaly_log_path):
        anomalies = pd.read_csv(anomaly_log_path)
        if head is None:
            st.dataframe(anomalies)
        else:
            st.dataframe(anomalies.head(head))
    else:
        st.error("Anomaly log not found.")
    return



COL = st.columns(2)

if datetime.now(timezone.utc)-st.session_state.now>pd.Timedelta(seconds=10): 
    st.session_state.now = datetime.now(timezone.utc)
with COL[0]:
    station_health_check()  


with COL[1]:
    st.markdown("<h3 style='text-align: center;'>Anomaly log</h3>", unsafe_allow_html=True)
    # anomalies = pd.read_csv("data/involcan/metadata/anomaly_log.csv")
    # anomalies
    anomaly_log(100)






