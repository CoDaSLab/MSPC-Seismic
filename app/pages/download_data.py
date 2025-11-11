from config import *
from widgets.forms import *
from utils.functions import get_stations, load_stations

from data.involcan.pull_rt import download_files_rt

# --- Application start ---
init_page("Location Map")
init_session_state()
st.title('Data download')
# ------------------------

group = st.session_state.group
group_stations = get_stations(group["name"])
all_stations = load_stations(column="code")

if all_stations is None:
    st.error(f"Data download is not available because the station catalog file ('{config["paths"]["station_catalog"]}') does not exist.")
else:
    current_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    noc_start_day = current_day - timedelta(days=st.session_state.config["monitoring"]["num_days_noc_length"])

    key = "download_data"
    starttime, endtime = select_time(key, default_start=noc_start_day, default_end=current_day)
    network = st.text_input("Network", value=group["network"])
    stations, channels = multi_select_station(key, all_stations, default_stations=all_stations, channel_list=group["channels"],default_channels=group["channels"])

    download_button = st.button("Download files", type="primary", use_container_width=True)

    with st.spinner("Downloading files. Please wait, this might take a while...", show_time=True):
        if download_button:
            data_path = st.session_state.config["paths"]["data"]
            ip = st.session_state.config["connection"]["server_IP"]
            user = st.session_state.config["connection"]["server_user"]
            ssh_key = st.session_state.config["connection"]["ssh_key_path"]

            successful_downloads, failed_downloads = download_files_rt(
                starttime, endtime,
                ip, user, network,
                stations, channels, data_path=data_path, key_path=ssh_key,
                update_latest=False)
            
            st.success(f"{successful_downloads} files were downloaded")
            if failed_downloads > 0:
                st.warning(f"{failed_downloads} files were not downloaded")

