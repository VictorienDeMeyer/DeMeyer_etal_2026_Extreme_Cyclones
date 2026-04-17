#!/bin/bash
#SBATCH --time=20:00:00
#SBATCH --account=rrg-gachon
#SBATCH --ntasks=1

module load python/3.11 mpi4py/4.0.3 scipy-stack/2024a geos proj; source /home/vdemeyer/py3/bin/activate

# python /home/vdemeyer/TRACKING/KATJA/PREPROCESSING/Calculate_Percentile.py --variable $variable --sim $sim --cond
python /home/vdemeyer/TRACKING/KATJA/PREPROCESSING/Calculate_Percentile.py --variable $variable --sim $sim