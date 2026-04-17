#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --time=00:12:00
#SBATCH --ntasks=1
#SBATCH --mem=40G
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null

module load python/3.11 mpi4py/4.0.3 scipy-stack/2024a geos proj; source /home/vdemeyer/py3/bin/activate

# python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/concat_contribution_ETCs.py --future --only-merge
python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/concat_contribution_ETCs.py --only-merge