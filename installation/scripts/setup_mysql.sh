#!/bin/bash

# --- Argument Gatherer Script ---
echo "--- MySQL Setup Configuration ---"
read -r -p "Do you want to proceed with the MySQL configuration setup? (y/N): " proceed_setup

# Convert input to lowercase for robust comparison
proceed_setup=$(echo "$proceed_setup" | tr '[:upper:]' '[:lower:]')

if [[ "$proceed_setup" != "y" ]]; then
    echo "MySQL configuration setup skipped. Exiting script."
    exit 0
fi

echo "Proceeding with MySQL configuration..."
# Assign command line arguments to variables
MYSQL_USER="${1}"
MYSQL_DATABASE="${2}"
MYSQL_PASSWORD="${3}"
MYSQL_QUERY="${4}"

# Function to prompt the user for missing input
get_input() {
    local var_name=$1
    local prompt=$2
    local is_sensitive=$3
    local current_value="${!var_name}"

    while [ -z "$current_value" ]; do
        echo ""
        # Handle password input without echoing characters
        if [ "$is_sensitive" = "true" ]; then
            read -r -s -p "Missing argument: $prompt. Please enter it: " current_value
        else
            read -r -p "Missing argument: $prompt. Please enter it: " current_value
        fi
    done
    
    # Assign the captured value back to the original variable
    # Use eval to handle variable names dynamically
    eval "$var_name=\"$current_value\""
}

# 1. Ensure MYSQL_USER is provided
if [ -z "$MYSQL_USER" ]; then
    get_input MYSQL_USER "MySQL Username" "false"
fi

# 2. Ensure MYSQL_DATABASE is provided
if [ -z "$MYSQL_DATABASE" ]; then
    get_input MYSQL_DATABASE "MySQL Database Name" "false"
fi

# 3. Ensure MYSQL_PASSWORD is provided (sensitive input, using 'true')
if [ -z "$MYSQL_PASSWORD" ]; then
    get_input MYSQL_PASSWORD "MySQL Password" "true"
fi
# 3. Ensure MYSQL_QUERY is provided (sensitive input, using 'true')
if [ -z "$MYSQL_QUERY" ]; then
    get_input MYSQL_QUERY "MySQL Query" "true"
fi

# 4. Execute the Operations script with the now guaranteed arguments
echo ""
echo "--- MySQL Arguments gathered successfully. Executing Operations Script ---"
echo ""
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
"$SCRIPT_DIR"/setup_mysql_config.sh "$MYSQL_USER" "$MYSQL_DATABASE" "$MYSQL_PASSWORD" "$MYSQL_QUERY"