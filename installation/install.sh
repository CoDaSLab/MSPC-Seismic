#!/bin/bash

# --- 1. Variable Assignment and Validation ---
USER_SSH=$1
IP_HOST=$2
KEY_NAME=${3:-id_ed25519}

MYSQL_USER=${4:-""}
MYSQL_DATABASE=${4:-""}

directory=$(dirname "$0")

echo ""
echo "STEP 1: Generating ssh key for connection to server..."
sleep 1
"$directory"/scripts/setup_ssh_key.sh "$REMOTE_USER" "$TARGET_IP" "$CUSTOM_KEY"

echo ""
echo "STEP 2: Download and install conda"
"$directory"/scripts/install_conda.sh

echo ""
echo "STEP 3: Create enviroment lafragua..."
sleep 1
yes | "$directory"/scripts/create_enviroment.sh

CONDA_BASE=$(conda info --base)
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate lafragua

echo ""
echo "STEP 4: Creating configuration file based on template..."
sleep 1
"$directory"/scripts/setup_config.sh "$REMOTE_USER" "$TARGET_IP" "$CUSTOM_KEY" "$MYSQL_USER" "$MYSQL_DATABASE"

echo ""
echo "STEP 5: Activating crontab command for realtime data downloads..."
sleep 1
python3 "$directory"/scripts/cron_setup.py

echo ""
echo "--- INSTALLATION COMPLETE ---"
echo ""

echo "Launching application..."
nohup streamlit run app/home.py > app/log.out &



