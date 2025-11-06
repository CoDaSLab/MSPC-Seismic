#!/bin/bash
set -e

install_jq() {
    if command -v apt &> /dev/null; then
        echo "jq not found. Installing via apt..."
        sudo apt update > /dev/null 2>&1
        sudo apt install -y jq
    elif command -v dnf &> /dev/null; then
        echo "jq not found. Installing via dnf..."
        sudo dnf install -y jq
    elif command -v yum &> /dev/null; then
        echo "jq not found. Installing via yum..."
        sudo yum install -y jq
    else
        echo "Error: Cannot find apt, dnf, or yum to install jq. Please install jq manually." >&2
        exit 1
    fi
    if ! command -v jq &> /dev/null; then
        echo "Error: jq failed to install." >&2
        exit 1
    fi
}

if ! command -v jq &> /dev/null; then
    install_jq
fi

USER=$1
IP=$2
KEY_PATH=$3

MYSQL_USER=$4
MYSQL_DATABASE=$5

CONFIG_FILE="config.json"
BASE_DIR=$(dirname "$0")

if [ -z "$USER" ] || [ -z "$IP" ] || [ -z "$KEY_PATH" ]; then
    echo "Error: Missing required arguments (User, IP, Key Path)." >&2
    echo "Usage: $0 <user> <ip> <key_path> [mysql_user] [mysql_database]" >&2
    exit 1
fi

echo "Creating $CONFIG_FILE based on template..."
cp -n config_template.json config.json

echo "Updating $CONFIG_FILE with new configuration..."

jq --arg user "$USER" \
   --arg ip "$IP" \
   --arg keypath "$KEY_PATH" \
   '
     .connection.server_user = $user |
     .connection.server_IP = $ip |
     .connection.ssh_key_path = $keypath
   ' "$CONFIG_FILE" > temp.$CONFIG_FILE && mv temp.$CONFIG_FILE "$CONFIG_FILE"

echo ""
echo "Configuration updated successfully in $CONFIG_FILE."
echo "User: $USER, IP: $IP, Key Path: $KEY_PATH"

if [ -n "$MYSQL_USER" ] && [ -n "$MYSQL_DATABASE" ]; then
    echo "--- MySQL Configuration ---"
    
    read -r -s -p "Enter MySQL Password: " MYSQL_PASSWORD
    echo
    
    read -r -p "Enter MySQL Query to use: " MYSQL_QUERY
    
    echo "Updating MySQL connection fields in $CONFIG_FILE..."

    jq --arg mysql_user "$MYSQL_USER" \
       --arg mysql_password "$MYSQL_PASSWORD" \
       --arg mysql_query "$MYSQL_QUERY" \
       '
         .connection.mysql_connection.mysql_update = true |
         .connection.mysql_connection.user = $mysql_user |
         .connection.mysql_connection.password = $mysql_password |
         .connection.mysql_connection.database_name = "'"$MYSQL_DATABASE"'" |
         .connection.mysql_connection.query = $mysql_query
       ' "$CONFIG_FILE" > temp.$CONFIG_FILE && mv temp.$CONFIG_FILE "$CONFIG_FILE"

    echo "MySQL configuration applied successfully."
    
    UPDATE_SCRIPT="../../monitoring/update_stations.sh"
    FULL_SCRIPT_PATH="$BASE_DIR/$UPDATE_SCRIPT"

    echo "Executing supplementary script: $UPDATE_SCRIPT"
    if [ -x "$FULL_SCRIPT_PATH" ]; then
        "$FULL_SCRIPT_PATH"
        echo "Supplementary script executed."
    else
        echo "Error: Supplementary script not found or lacks execution permission: $FULL_SCRIPT_PATH" >&2
        exit 1
    fi

elif [ -n "$MYSQL_USER" ] || [ -n "$MYSQL_DATABASE" ]; then
    echo ""
    echo "Error: MySQL configuration arguments incomplete." >&2
    echo "To configure MySQL, you must provide BOTH <mysql_user> AND <mysql_database>." >&2
    exit 1
fi