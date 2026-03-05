#!/bin/bash
#SBATCH --time=00:55:00
#SBATCH --account=rrg-gachon
#SBATCH --mem=50G
#SBATCH --ntasks=1

module load python/3.11 mpi4py/4.0.3 scipy-stack/2024a geos proj; source /home/vdemeyer/py3/bin/activate

python /home/vdemeyer/TRACKING/KATJA/PREPROCESSING/preprocess_year.py $year --sim $sim