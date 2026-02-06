#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --time=01:20:00
#SBATCH --ntasks=1
#SBATCH --mem=60G

module load python/3.11 mpi4py/4.0.3 scipy-stack/2024a geos proj; source /home/vdemeyer/py3/bin/activate

python /home/vdemeyer/TRACKING/KATJA/PREPROCESSING/slice_decade_preprocess.py $sim --start_year $start_year --end_year $end_year