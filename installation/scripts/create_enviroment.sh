#!/bin/bash
set -e

conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main || true
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r || true

conda create --name lafragua python=3.12 -y
bash -i -c "conda init && conda activate lafragua && pip install -r ./installation/requirements.txt"
