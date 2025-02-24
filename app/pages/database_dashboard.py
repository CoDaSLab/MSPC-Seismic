from config import *

from utils.functions import load_data
from widgets.tables import show_table, check_availability, filter_dataframe
from widgets.forms import select_time

# --- Application start ---
init_page("Digivolcan Database")
init_session_state()
st.title('Digivolcan database dashboard')
# ------------------------

# csv files to load
csv_files = {
    "Available Files":      "data/metadata/Available_files.csv",
    # "Available Time":       "data/metadata/Available_times.csv",
    # "Available Events":     "data/metadata/ivc_available_data.csv",
    "Feature Log":          "data/metadata/feature_log.csv",
}
names = list(csv_files.keys())
paths = list(csv_files.values())

names.append('Check data availability')
tabs = st.tabs(names)

# Show tables in each of the tabs
for id, tab in enumerate(tabs[:-1]):
    with tab:
        data = load_data(paths[id])
        data = filter_dataframe(data)
        show_table(data)

# Check data availability
with tabs[-1]:
    check_availability(paths[0], paths[1])