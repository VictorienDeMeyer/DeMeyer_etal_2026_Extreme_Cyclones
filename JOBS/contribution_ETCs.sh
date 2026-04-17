#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --time=01:15:00
#SBATCH --ntasks=1
#SBATCH --mem=50G

module load python/3.11 mpi4py/4.0.3 scipy-stack/2024a geos proj; source /home/vdemeyer/py3/bin/activate

# python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/contribution_ETCs.py $iyear --sim $sim --var $var --future
python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/contribution_ETCs.py $iyear --sim $sim --var $var