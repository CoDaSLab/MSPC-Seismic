#!/bin/bash
set -e

echo "accepting conda's terms of service..."
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main || true
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r || true

sleep 1
echo ""

echo Creating enviroment...
conda create --name lafragua python=3.12 -y
echo ""

directory=$(dirname "$0")
source "$directory"/../miniconda3/etc/profile.d/conda.sh 
conda activate lafragua
pip install -r ./installation/requirements.txt

# bash -i -c "conda activate lafragua && pip install -r ./installation/requirements.txt"
