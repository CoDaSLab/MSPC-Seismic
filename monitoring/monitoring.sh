#!/bin/bash

REPO_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )
CONFIG_FILE="${REPO_DIR}/config.json"

# Change directory
cd $REPO_DIR

# Enter conda environment
source ${REPO_DIR}/installation/miniconda3/bin/activate lafragua


# -- PULL THE DATA FROM THE SERVER --
LOG_FILE="${REPO_DIR}/monitoring/logs/pull.log"
ERROR_FILE="${REPO_DIR}/monitoring/logs/pull_error.log"

# Create directories and logs if they do not exist
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE" "$ERROR_FILE"

# Read configuration file
auto_monitoring=$(jq -r '.monitoring.auto_monitoring' "$CONFIG_FILE")
server_ip=$(jq -r '.connection.server_IP' "$CONFIG_FILE")
server_user=$(jq -r '.connection.server_user' "$CONFIG_FILE")
ssh_key=$(jq -r '.connection.ssh_key_path' "$CONFIG_FILE")
pull_times_log=$(jq -r '.paths.latest_pulls_log' "$CONFIG_FILE")
data_path=$(jq -r '.paths.data' "$CONFIG_FILE")

# Extract group names
mapfile -t groups < <(jq -r '.groups | keys[]' "$CONFIG_FILE")

all_stations=()
all_channels=()
all_networks=()

# Iterate over all groups and collect stations, channels, and networks
for group in "${groups[@]}"; do
    network=$(jq -r ".groups[\"$group\"].network" "$CONFIG_FILE")
    mapfile -t stations < <(jq -r ".groups[\"$group\"].stations[]" "$CONFIG_FILE")
    mapfile -t channels < <(jq -r ".groups[\"$group\"].channels[]" "$CONFIG_FILE")

    all_stations+=("${stations[@]}")
    all_channels+=("${channels[@]}")
    all_networks+=("$network")
done

# Remove duplicates
all_stations=($(printf "%s\n" "${all_stations[@]}" | sort -u))
all_channels=($(printf "%s\n" "${all_channels[@]}" | sort -u))
all_networks=($(printf "%s\n" "${all_networks[@]}" | sort -u))

# Log configuration info
echo "Networks: ${all_networks[*]}" >> "$LOG_FILE"
echo "Stations: ${all_stations[*]}" >> "$LOG_FILE"
echo "Channels: ${all_channels[*]}" >> "$LOG_FILE"


echo "[$(date)] Downloading data..." >> "$LOG_FILE"

# Define time range (UTC)
today=$(date -u -d "now - 6 minute" +'%Y-%m-%d 00:00:00')
now=$(date -u +'%Y-%m-%d %H:%M:%S')

# Run download for each network
for network in "${all_networks[@]}"; do

    python -m data.involcan.pull_rt "$today" "$now" "${server_ip}" "${server_user}" "$network" \
        -s "${all_stations[@]}" \
        -c "${all_channels[@]}" \
        --log_path "$pull_times_log" \
        --data_path "$data_path" \
        --key_path "${ssh_key}" \
        -u >> "$LOG_FILE" 2>> "$ERROR_FILE"

    # If there was an error, log it
    if [ $? -ne 0 ]; then
        echo >> "$ERROR_FILE"
        echo "[$(date)] ERROR while downloading data for network $network." >> "$ERROR_FILE"
        echo >> "$ERROR_FILE"
        echo "==============================================================" >> "$ERROR_FILE"
        echo >> "$ERROR_FILE"
        echo "ERROR: Download failed for network $network. See $ERROR_FILE." >> "$LOG_FILE"
    fi
done

echo >> "$LOG_FILE"
echo "==============================================================" >> "$LOG_FILE"
echo >> "$LOG_FILE"



# -- EXECUTE ANOMALY MONITORING CALCULATIONS --
if [ "$auto_monitoring" = "true" ]; then

    LOG_FILE="${REPO_DIR}/monitoring/logs/monitoring.log"
    ERROR_FILE="${REPO_DIR}/monitoring/logs/monitoring_error.log"

    # Create directories and logs if they do not exist
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE" "$ERROR_FILE"

    # Check if script is already running
    if [ "$(jq -r '.metadata.running' "$CONFIG_FILE")" = "true" ]; then
        MSG="[$(date)] A previous execution is still ongoing. Aborting."
        echo "$MSG" >> "$LOG_FILE"
        exit 1
    fi

    echo "[$(date)] Running monitoring script..." >> "$LOG_FILE"

    # Restore "running" state after finishing or in case of error
    cleanup() {
        jq '.metadata.running = false' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    }
    trap cleanup EXIT

    # Set monitoring scripts to "running"
    jq '.metadata.running = true' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"

    # Run monitoring script
    python -m monitoring.main --config "$CONFIG_FILE" >> "$LOG_FILE" 2>> "$ERROR_FILE"

    # In case of error, write messages in ERROR_FILE
    if [ $? -ne 0 ]; then
        echo >> "$ERROR_FILE"
        echo "[$(date)] ERROR when monitoring." >> "$ERROR_FILE"
        echo >> "$ERROR_FILE"
        echo "==============================================================" >> "$ERROR_FILE"
        echo >> "$ERROR_FILE"
        echo >> "$LOG_FILE"
        echo "ERROR: Monitoring failed. See $ERROR_FILE." >> "$LOG_FILE"
    fi

    echo >> "$LOG_FILE"
    echo "==============================================================" >> "$LOG_FILE"
    echo >> "$LOG_FILE"
fi