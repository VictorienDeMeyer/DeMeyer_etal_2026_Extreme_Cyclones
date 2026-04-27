#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --time=00:45:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=50G
#SBATCH --array=0-279%100
#SBATCH --job-name=ETCs_1000km
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/ETCs_1000km_%A_%a.out

# 280 tasks total:
#   8 sims x 35 years = 280
#   ERA5/UBB/UBD/UBE/UBF: 1980-2014
#   UBG/UBH/UBI: 2063-2097

module load python/3.11 mpi4py/4.0.3 esmf scipy-stack/2024a geos proj
source /home/vdemeyer/py3/bin/activate

tasks=()
for sim in ERA5 UBB UBD UBE UBF; do
  for year in $(seq 1980 2014); do
    tasks+=("$sim $year")
  done
done
for sim in UBG UBH UBI; do
  for year in $(seq 2063 2097); do
    tasks+=("$sim $year")
  done
done

read sim year <<< "${tasks[$SLURM_ARRAY_TASK_ID]}"

echo "Array task $SLURM_ARRAY_TASK_ID : sim=$sim year=$year"

python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/ETCs_1000km.py "$year" --sim "$sim"

# Submit: sbatch /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_ETCs_1000km.sh
# Resubmit a subset: sbatch --array=12,45,67 /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_ETCs_1000km.sh
