#!/bin/bash

REPO_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )
CONFIG_FILE="${REPO_DIR}/monitoring/config.json"
# Change directory
cd $REPO_DIR

# Enter conda environment
source ${REPO_DIR}/installation/miniconda3/bin/activate lafragua


# -- PULL THE DATA FROM THE SERVER --
LOG_FILE="${REPO_DIR}/monitoring/logs/pull.log"
ERROR_FILE="${REPO_DIR}/monitoring/logs/pull_error.log"
# Read configuration file
server_ip=$(jq -r '.server_IP' "$CONFIG_FILE")
server_user=$(jq -r '.server_user' "$CONFIG_FILE")
ssh_key=$(jq -r '.ssh_key_path' "$CONFIG_FILE")
pull_times_log=$(jq -r '.latest_pulls_log_path' "$CONFIG_FILE")
data_path=$(jq -r '.data_path' "$CONFIG_FILE")
network=$(jq -r '.network' "$CONFIG_FILE")
mapfile -t stations < <(jq -r '.stations[]' "$CONFIG_FILE")
mapfile -t channels < <(jq -r '.channels[]' "$CONFIG_FILE")

echo "stations: ${stations[@]}" >> "$LOG_FILE"
echo "channels: ${channels[@]}" >> "$LOG_FILE"

sleep 2

echo "[$(date)] Dowloading files..." >> "$LOG_FILE"
today=$(date -u -d "now - 6 minute" +'%Y-%m-%d 00:00:00')
now=$(date -u +'%Y-%m-%d %H:%M:%S')

# Download files from server. Stores output and errors in different logs.
python -m data.involcan.pull_rt "$today" "$now" "${server_ip}" "${server_user}" "$network" -kp "${ssh_key}" -s "${stations[@]}" -c "${channels[@]}" --log_path "$pull_times_log" --data_path "$data_path" >> "$LOG_FILE" 2>> "$ERROR_FILE"

# In case of error, write messages in ERROR_FILE
if [ $? -ne 0 ]; then
    echo >> "$ERROR_FILE"
    echo "[$(date)] ERROR when downloading files." >> "$ERROR_FILE"
    echo >> "$ERROR_FILE"
    echo "==============================================================" >> "$ERROR_FILE"
    echo >> "$ERROR_FILE"
    echo >> "$LOG_FILE"
    echo "ERROR: Download failed. See $ERROR_FILE." >> "$LOG_FILE"
fi

echo >> "$LOG_FILE"
echo "==============================================================" >> "$LOG_FILE"
echo >> "$LOG_FILE"


# -- EXECUTE ANOMALY MONITORING CALCULATIONS --
LOG_FILE="${REPO_DIR}/monitoring/logs/monitoring.log"
ERROR_FILE="${REPO_DIR}/monitoring/logs/monitoring_error.log"

echo "[$(date)] Running monitoring script..." >> "$LOG_FILE"

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