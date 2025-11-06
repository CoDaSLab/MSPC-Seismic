#!/bin/bash
conda create --name lafragua python=3.12
bash -i -c "conda init && conda activate lafragua && pip install -r ./installation/requirements.txt"
