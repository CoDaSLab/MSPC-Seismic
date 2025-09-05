from config import *
from widgets import maps
from utils.functions import load_last_pulls, load_stations

from datetime import datetime, timezone
import pandas as pd


# --- Application start ---
init_page("Digivolcan Home")
init_session_state()

st.markdown("---")
# st.markdown("<h1 style='text-align: center;'>Digivolcan Home</h1>", unsafe_allow_html=True)

COL = st.columns(2)

with COL[0]:
    st.markdown("<h3 style='text-align: center;'>Running stations</h3>", unsafe_allow_html=True)
    last_pulls = load_last_pulls()
    stations = load_stations()

    now = datetime.now(timezone.utc)
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
        time = max(station_rows["time_since_last_pull"])

        if   time < pd.Timedelta(minutes=5): color = "green" 
        elif time < pd.Timedelta(minutes=10): color = "orange" 
        else: color = "red" 

        active_stations_dic['station'].append(active_station)
        active_stations_dic['time_since_last_pull'].append(time)
        active_stations_dic['color'].append(color)
        active_stations_dic['popup'].append("\nLast update:")

    # Display the Map
    map = maps.create_map()
    map = maps.add_stations(map, stations[stations['station'].isin(active_stations)],
                            color=active_stations_dic['color'],
                            popup=active_stations_dic['popup'])
    maps.show_map(map)

    """
    Calculamos la diferencia entre la última descarga y la hora actual en UTC. 
    Dependiendo de este valor (en minutos?), coloreamos de una forma u otra los markers
    del mapa.

    Al poner el ratón encima de un marker veremos: El nombre de la estación, y la última hora de
    actualización.

    Si hace más de 1 mes de la última actualización, no se muestra el sensor en el mapa

    Ya que cada estación cuenta con 3 canales, el tiempo que mostraremos seŕa el mayor de los 3
    """    

    # maps.draw_map()


with COL[1]:
    st.markdown("<h3 style='text-align: center;'>Anomaly log</h3>", unsafe_allow_html=True)
    anomalies = pd.read_csv("data/involcan/metadata/anomaly_log.csv")
    anomalies