#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --time=01:15:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=40G
#SBATCH --array=0-559%100
#SBATCH --job-name=contrib_ETCs
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/contrib_ETCs_%A_%a.out

# 560 tasks total:
#   8 sims x 2 vars x 35 years = 560
#   ERA5/UBB/UBD/UBE/UBF: 1980-2014
#   UBG/UBH/UBI: 2063-2097

module load python/3.11 mpi4py/4.0.3 scipy-stack/2024a geos proj
source /home/vdemeyer/py3/bin/activate

tasks=()
for sim in ERA5 UBB UBD UBE UBF; do
  for var in pr ws; do
    for year in $(seq 1980 2014); do
      tasks+=("$sim $var $year")
    done
  done
done
for sim in UBG UBH UBI; do
  for var in pr ws; do
    for year in $(seq 2063 2097); do
      tasks+=("$sim $var $year")
    done
  done
done

read sim var year <<< "${tasks[$SLURM_ARRAY_TASK_ID]}"

echo "Array task $SLURM_ARRAY_TASK_ID : sim=$sim var=$var year=$year"

python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/contribution_ETCs.py "$year" --sim "$sim" --var "$var"

# Submit: sbatch /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_contribution_ETCs.sh
# Resubmit a subset: sbatch --array=12,45,67 /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_contribution_ETCs.sh
