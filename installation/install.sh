#!/bin/bash
set -e

# --- 1. Variable Assignment and Validation ---
REMOTE_USER=$1
TARGET_IP=$2
CUSTOM_KEY=${3:-id_ed25519}

MYSQL_USER=${4:-""}
MYSQL_DATABASE=${5:-""}

directory=$(dirname "$0")

echo ""
echo "STEP 1: Generating ssh key for connection to server..."
sleep 1
SSH_KEY_PATH="$("$directory"/scripts/setup_ssh_key.sh "$REMOTE_USER" "$TARGET_IP" "$CUSTOM_KEY" 5>&1 1>/dev/tty)"

echo ""
echo "STEP 2: Creating configuration file based on template..."
sleep 1
"$directory"/scripts/setup_config.sh "$REMOTE_USER" "$TARGET_IP" "$SSH_KEY_PATH" 


echo ""
echo "STEP 3: Get mysql configuration (optional)"
sleep 1
IFS='|' read -r MYSQL_USER MYSQL_DATABASE MYSQL_PASSWORD MYSQL_QUERY \
  <<< "$("$directory"/scripts/setup_mysql_config.sh "$MYSQL_USER" "$MYSQL_DATABASE" 5>&1 1>/dev/tty)"

echo ""
echo "STEP 4: Download and install conda"
sleep 1
"$directory"/scripts/install_conda.sh

echo ""
echo "STEP 5: Create enviroment lafragua..."
sleep 1
yes | "$directory"/scripts/create_enviroment.sh

CONDA_BASE=$(conda info --base)
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate lafragua

echo ""
echo "STEP 6: Updating mysql configuration..."
sleep 1
"$directory"/scripts/setup_mysql_config.sh "$MYSQL_USER" "$MYSQL_DATABASE" "$MYSQL_PASSWORD" "$MYSQL_QUERY"

echo ""
echo "STEP 7: Activating crontab command for realtime data downloads..."
sleep 1
python3 "$directory"/scripts/cron_setup.py

echo ""
echo "--- INSTALLATION COMPLETE ---"
echo ""

echo "Launching application..."
nohup streamlit run app/home.py > app/log.out &



