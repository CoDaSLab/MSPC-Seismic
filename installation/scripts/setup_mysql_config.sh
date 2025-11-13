#!/bin/bash
set -e

install_jq() {
    if command -v jq &> /dev/null; then
        return
    fi

    echo "jq not found. Installing..."
    if command -v apt &> /dev/null; then
        sudo apt update -y >/dev/null 2>&1
        sudo apt install -y jq >/dev/null 2>&1
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y jq >/dev/null 2>&1
    elif command -v yum &> /dev/null; then
        sudo yum install -y jq >/dev/null 2>&1
    else
        echo "Error: Cannot find apt, dnf, or yum to install jq. Please install jq manually." >&2
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        echo "Error: jq failed to install." >&2
        exit 1
    fi
}

install_jq

MYSQL_USER=$1
MYSQL_DATABASE=$2
MYSQL_PASSWORD=$3
MYSQL_QUERY=$4
MYSQL_QUERY="${MYSQL_QUERY//\\n/ }"


CONFIG_FILE="config.json"
BASE_DIR=$(dirname "$0")


# --- Si todos los valores están presentes: actualizar config.json ---
echo "--- MySQL Configuration ---"
echo "Updating MySQL connection fields in $CONFIG_FILE..."

jq --arg mysql_user "$MYSQL_USER" \
   --arg mysql_password "$MYSQL_PASSWORD" \
   --arg mysql_query "$MYSQL_QUERY" \
   --arg mysql_database "$MYSQL_DATABASE" \
   '
     .connection.mysql_connection.mysql_update = true |
     .connection.mysql_connection.user = $mysql_user |
     .connection.mysql_connection.password = $mysql_password |
     .connection.mysql_connection.database_name = $mysql_database |
     .connection.mysql_connection.query = $mysql_query
   ' "$CONFIG_FILE" > temp.$CONFIG_FILE && mv temp.$CONFIG_FILE "$CONFIG_FILE"

echo "MySQL configuration applied successfully."

# --- Ejecutar script suplementario ---
UPDATE_SCRIPT="../../monitoring/update_stations.sh"
FULL_SCRIPT_PATH="$BASE_DIR/$UPDATE_SCRIPT"
CONDA_ACTIVATE_SCRIPT="./installation/miniconda3/bin/activate"

echo "Executing supplementary script: $FULL_SCRIPT_PATH"
if [ -x "$FULL_SCRIPT_PATH" ]; then
    bash -c "
    source \"$CONDA_ACTIVATE_SCRIPT\" lafragua &&
    \"$FULL_SCRIPT_PATH\"
    "
    echo "Supplementary script executed."
else
    echo "Error: Supplementary script not found or lacks execution permission: $FULL_SCRIPT_PATH" >&2
    exit 1
fi
