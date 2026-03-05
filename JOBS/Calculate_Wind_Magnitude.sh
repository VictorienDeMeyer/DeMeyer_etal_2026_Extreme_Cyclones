#!/bin/bash
#SBATCH --time=18:00:00
#SBATCH --account=rrg-gachon
#SBATCH --mem=32G
#SBATCH --ntasks=1

cd /home/vdemeyer/TRACKING/KATJA/PREPROCESSING/

module load python/3.11 mpi4py/4.0.3 scipy-stack/2024a geos proj; source /home/vdemeyer/py3/bin/activate

python Calculate_Wind_Magnitude.py $sim