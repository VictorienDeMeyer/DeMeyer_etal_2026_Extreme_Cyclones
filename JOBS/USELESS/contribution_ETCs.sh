#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --time=12:00:00
#SBATCH --ntasks=1
#SBATCH --mem=32G

module load python/3.11 mpi4py/4.0.3 esmf scipy-stack/2024a geos proj; source /home/vdemeyer/py3/bin/activate

python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/contribution_ETCs.py --sim $sim --var $var