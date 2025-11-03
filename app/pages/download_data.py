from config import *
from widgets.forms import *
from utils.functions import get_stations

from data.involcan.pull_rt import download_files_rt

# --- Application start ---
init_page("Location Map")
init_session_state()
# st.title('Data mapping')
# ------------------------

group = st.session_state.group
group_stations = get_stations(group["name"])
all_stations = config["data"]["stations"]

current_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
noc_start_day = current_day - timedelta(days=st.session_state.config["monitoring"]["num_days_noc_length"])

COL = st.columns(1)

with COL[0]:
    key = "download_data"
    starttime, endtime = select_time(key, default_start=noc_start_day, default_end=current_day)
    stations, channels = multi_select_station(key, all_stations, default_stations=all_stations, default_channels=group["channels"])

    download_button = st.button("Download files", type="primary", use_container_width=True)


    with st.spinner("Downloading files. Please wait, this might take a while...", show_time=True):
        if download_button:

            data_path = st.session_state.config["paths"]["data"],
            ip = st.session_state.config["connection"]["server_IP"],
            user = st.session_state.config["connection"]["server_user"],
            ssh_key = st.session_state.config["connection"]["ssh_key_path"],
            network = st.session_state.group["network"],

            successful_downloads, failed_downloads = download_files_rt(
                starttime, endtime,
                ip[0], user[0], network[0],
                stations, channels, data_path=data_path[0], key_path=ssh_key[0],
                update_latest=False)
            
            st.success(f"{successful_downloads} files were downloaded")
            if failed_downloads > 0:
                st.warning(f"{failed_downloads} files were not downloaded")

