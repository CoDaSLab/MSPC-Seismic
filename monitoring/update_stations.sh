#!/bin/bash
REPO_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )
CONFIG_FILE="${REPO_DIR}/config.json"
python -m monitoring.update_stations --config "$CONFIG_FILE"