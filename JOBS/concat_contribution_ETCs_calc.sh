#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --time=01:00:00
#SBATCH --ntasks=1
#SBATCH --mem=32G
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null

module load python/3.11 mpi4py/4.0.3 scipy-stack/2024a geos proj
source /home/vdemeyer/py3/bin/activate

sims=($sims_str)
sim=${sims[$SLURM_ARRAY_TASK_ID]}

python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/concat_contribution_ETCs.py --sim $sim --only-calc
