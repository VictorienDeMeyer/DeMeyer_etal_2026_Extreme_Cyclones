#!/bin/bash
#SBATCH --job-name=EETCs_stat
#SBATCH --account=rrg-gachon
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/output_%j.txt
#SBATCH --error=/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/error_%j.txt
#SBATCH --time=02:00:00
#SBATCH --ntasks=1
#SBATCH --mem=20G

module load python/3.11 mpi4py/4.0.3 scipy-stack/2024a geos proj; source /home/vdemeyer/py3/bin/activate

python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/EETCs_stat.py $iyear