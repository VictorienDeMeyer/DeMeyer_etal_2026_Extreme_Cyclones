#!/bin/bash
#SBATCH --time=05:00:00
#SBATCH --account=rrg-gachon
#SBATCH --mem=32G
#SBATCH --ntasks=1
#SBATCH -o /home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/chunk_decade_preprocess.out
#SBATCH --job-name=DECADE_SLP

cd /home/vdemeyer/TRACKING/KATJA/PREPROCESSING/

module load python/3.11 mpi4py/4.0.3 scipy-stack/2024a geos proj; source /home/vdemeyer/py3/bin/activate

python chunk_decade_preprocess.py

#sbatch /home/vdemeyer/TRACKING/KATJA/JOBS/chunk_decade_preprocess.sh