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

CONFIG_FILE="config.json"
BASE_DIR=$(dirname "$0")

# --- Caso: user y database vacíos ---
if [ -z "$MYSQL_USER" ] || [ -z "$MYSQL_DATABASE" ]; then
    echo " " >&2
    echo ":: No MySQL credentials provided. Skipping configuration.">&2
    echo "$MYSQL_USER|$MYSQL_DATABASE|$MYSQL_PASSWORD|$MYSQL_QUERY">&5
    exit 1
fi

# --- Preguntar valores faltantes ---
missing=0
if [ -z "$MYSQL_USER" ]; then
    read -r -p "Enter MySQL User: " MYSQL_USER
    missing=1
fi

if [ -z "$MYSQL_DATABASE" ]; then
    read -r -p "Enter MySQL Database: " MYSQL_DATABASE
    missing=1
fi

if [ -z "$MYSQL_PASSWORD" ]; then
    read -r -s -p "Enter MySQL Password: " MYSQL_PASSWORD
    echo "">&2
    missing=1
fi

if [ -z "$MYSQL_QUERY" ]; then
    read -r -p "Enter MySQL Query to use: " MYSQL_QUERY
    missing=1
fi

if [ "$missing" -eq 1 ]; then
    echo "Some parameters were missing. Exiting early.">&2
    echo "$MYSQL_USER|$MYSQL_DATABASE|$MYSQL_PASSWORD|$MYSQL_QUERY">&5
    exit 0
fi

# --- Si faltan aún user o database, no hacer nada ---
if [ -z "$MYSQL_USER" ] || [ -z "$MYSQL_DATABASE" ]; then
    echo ":: Incomplete MySQL parameters. Skipping configuration."
    echo "$MYSQL_USER|$MYSQL_DATABASE|$MYSQL_PASSWORD|$MYSQL_QUERY"
    exit 0
fi

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

echo "Executing supplementary script: $UPDATE_SCRIPT"
if [ -x "$FULL_SCRIPT_PATH" ]; then
    "$FULL_SCRIPT_PATH"
    echo "Supplementary script executed."
else
    echo "Error: Supplementary script not found or lacks execution permission: $FULL_SCRIPT_PATH" >&2
    exit 1
fi
