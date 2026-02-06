#!/bin/bash
#SBATCH --time=01:00:00
#SBATCH --account=rrg-gachon
#SBATCH --mem=300G
#SBATCH --ntasks=1
#SBATCH --job-name=concat_pickle_contribution_ETCs
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/concat_pickle_contribution_ETCs.out

module load python/3.11 mpi4py/4.0.3 scipy-stack/2024a geos proj; source /home/vdemeyer/py3/bin/activate

python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/concat_pickle_contribution_ETCs.py

# sbatch /home/vdemeyer/TRACKING/KATJA/JOBS/concat_pickle_contribution_ETCs.sh