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
# sleep 1
SSH_KEY_PATH="$("$directory"/scripts/setup_ssh_key.sh "$REMOTE_USER" "$TARGET_IP" "$CUSTOM_KEY" 5>&1 1>/dev/tty)"

echo ""
echo "STEP 2: Creating configuration file based on template..."
# sleep 1
"$directory"/scripts/setup_config.sh "$REMOTE_USER" "$TARGET_IP" "$SSH_KEY_PATH" 

echo ""
echo "STEP 3: Download and install conda"
# sleep 1
source "$directory"/scripts/install_conda.sh

echo ""
echo "STEP 4: Create enviroment lafragua..."
# sleep 1
source yes | "$directory"/scripts/create_enviroment.sh

echo ""
echo "STEP 5: (Optional) Configuring MySQL..."
# sleep 1
"$directory"/scripts/setup_mysql.sh "$MYSQL_USER" "$MYSQL_DATABASE" "$MYSQL_PASSWORD"

echo ""
echo "STEP 6: Activating crontab command for realtime data downloads..."
# sleep 1
python3 "$directory"/scripts/cron_setup.py

echo ""
echo "--- INSTALLATION COMPLETE ---"
echo ""
echo You can now launch the application using: bash launch_app.sh




