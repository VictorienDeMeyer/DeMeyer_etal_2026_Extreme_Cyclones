#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --time=00:40:00
#SBATCH --ntasks=1
#SBATCH --mem=32G
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null

module load python/3.11 mpi4py/4.0.3 scipy-stack/2024a geos proj; source /home/vdemeyer/py3/bin/activate

# python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/concat_contribution_ETCs.py --sim $sim --future --only-calc
python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/concat_contribution_ETCs.py --sim $sim --only-calc