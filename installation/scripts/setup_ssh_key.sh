#!/bin/bash

# --- 1. Variable Assignment and Validation ---
USER_SSH=$1
IP_HOST=$2
KEY_NAME=${3:-id_ed25519}

if [ -z "$USER_SSH" ] || [ -z "$IP_HOST" ]; then
    echo "Error: Missing required arguments."
    echo "Usage: $0 <username> <ip_address> [optional_key_name]"
    echo "Example 1 (Using default): $0 admin 192.168.1.10"
    echo "Example 2 (Using custom name): $0 admin 192.168.1.10 custom_key"
    exit 1
fi

KEY_PATH="$HOME/.ssh/$KEY_NAME"

echo "Remote User: $USER_SSH"
echo "Host IP: $IP_HOST"
echo "Key name to be used: **$KEY_NAME**"
echo "---"

# --- 2. Key Generation ---
mkdir -p ~/.ssh
cd ~/.ssh || { echo "Error: Could not access ~/.ssh"; exit 1; }

ssh-keygen -t ed25519 -f "$KEY_PATH" -N "" -C "$USER_SSH@$IP_HOST_key"

if [ ! -f "$KEY_PATH.pub" ]; then
    echo "Error generating SSH key at $KEY_PATH.pub"
    exit 1
fi

echo "Keys $KEY_NAME and $KEY_NAME.pub created successfully."
echo "---"

# --- 3. Key Copy to Server ---
echo "Copying public key $KEY_NAME.pub to $USER_SSH@$IP_HOST..."
ssh-copy-id -i "$KEY_PATH.pub" "$USER_SSH"@"$IP_HOST"

echo "Process completed. The private key is: $KEY_PATH"