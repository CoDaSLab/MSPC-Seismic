#!/bin/bash

REPO_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )
CONFIG_FILE="${REPO_DIR}/config.json"

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
full_path="$PROJECT_ROOT"/installation/miniconda3/etc/profile.d/conda.sh

source "$full_path"
conda init
conda activate lafragua

python -m monitoring.update_stations --config "$CONFIG_FILE"