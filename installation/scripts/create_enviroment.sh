#!/bin/bash
set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
full_path="$PROJECT_ROOT"/miniconda3/etc/profile.d/conda.sh
source "$full_path"

conda init
conda activate base

echo "Accepting conda's terms of service..."

conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main || true &&
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r || true

sleep 1
echo ""

echo Creating enviroment...
conda create --name lafragua python=3.12 -y
echo ""


conda activate lafragua
pip install -r ./installation/requirements.txt

