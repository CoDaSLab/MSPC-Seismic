#!/bin/bash
set -e

cd ./installation/
echo Downloading conda...
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

echo Installing conda...
bash Miniconda3-latest-Linux-x86_64.sh -b -p ./miniconda3

echo Deleting residual files...
rm Miniconda3-latest-Linux-x86_64.sh

echo Starting and updating conda...

cd ..

echo ""
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
full_path="$PROJECT_ROOT"/miniconda3/etc/profile.d/conda.sh
source "$full_path"

conda init
conda activate base
conda update conda --yes

conda --version
echo Installation finished!