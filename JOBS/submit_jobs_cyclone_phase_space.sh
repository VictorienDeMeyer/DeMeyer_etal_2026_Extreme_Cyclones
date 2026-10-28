#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --array=0-279%100
#SBATCH --job-name=cyclone_phase_space
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/cyclone_phase_space_%A_%a.out

# Cyclone phase space (Hart 2003) parameters along the tracks, one task per sim and year.
# 280 tasks total:
#   8 sims x 35 years = 280
#   ERA5/UBB/UBD/UBE/UBF: 1980-2014
#   UBG/UBH/UBI: 2063-2097
#
# Optional STRIDE env var: use one grid point every STRIDE points of the geopotential
# files (default 1: native grid).

STRIDE="${STRIDE:-1}"

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

echo "Array task $SLURM_ARRAY_TASK_ID : sim=$sim year=$year stride=$STRIDE"

python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/cyclone_phase_space.py "$year" --sim "$sim" --stride "$STRIDE"

# Submit: sbatch /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_cyclone_phase_space.sh
# Test on one task first (ERA5 1980 and UBD 1980): sbatch --array=0,70 /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_cyclone_phase_space.sh
# Resubmit a subset: sbatch --array=12,45,67 /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_cyclone_phase_space.sh
