#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --ntasks=1
#SBATCH --mem=6G

module load python/3.11 mpi4py/4.0.3 scipy-stack/2024a geos proj
source /home/vdemeyer/py3/bin/activate

if [ -n "$pairs_str" ]; then
    pairs=($pairs_str)
    pair=${pairs[$SLURM_ARRAY_TASK_ID]}
    sim=${pair%,*}
    season=${pair#*,}
else
    sims=($sims_str)
    sim=${sims[$SLURM_ARRAY_TASK_ID]}
fi

echo "Array task $SLURM_ARRAY_TASK_ID : sim=$sim season=$season"

python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/calculate_kde.py $sim $season
