#!/bin/bash
#SBATCH --nodes=5
#SBATCH --partition albaicin-fat
#SBATCH --job-name=digivolcan_pull
#SBATCH --error=/home/TIC270/gsus/DigiVolCan/error%j.err
#SBATCH --output=/home/TIC270/gsus/DigiVolCan/salida%j.out
#SBATCH --time=00:10:00

# python3 /home/TIC270/gsus/DigiVolCan/data/pull.py '2021-09-16 00:10:00' '2021-09-17 23:59:59' 'PA00' 'HHE' --path '/SCRATCH/TIC270/gsus/data/seismic'
python3 /home/TIC270/gsus/DigiVolCan/data/pull.py '2021-09-16 00:10:00' '2021-09-19 23:59:59' 'PA00' 'HHE'
python3 /home/TIC270/gsus/DigiVolCan/data/interruptions.py
# python3 /home/TIC270/gsus/DigiVolCan/data/pull.py '2021-09-17 00:10:00' '2021-09-20 19:59:59' 'PPMA' 'HHZ' --path '/SCRATCH/TIC270/gsus/data/seismic'
