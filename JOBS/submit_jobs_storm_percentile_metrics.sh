#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --time=00:20:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=35G
#SBATCH --array=0-419%100
#SBATCH --job-name=storm_percentile_metrics
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/storm_percentile_metrics_%A_%a.out

# 420 tasks total:
#   6 sims x 35 years x 2 quantiles = 420
#   hist (UBD, UBE, UBF): 1980-2014
#   future (UBG, UBH, UBI): 2063-2097
#
# Spatial mask: controlled by the MASK env var (land or urban). Passed through
# to the Python script via --mask. Defaults to 'land' if not exported.
#   sbatch --export=ALL,MASK=land  submit_jobs_storm_percentile_metrics.sh
#   sbatch --export=ALL,MASK=urban submit_jobs_storm_percentile_metrics.sh
MASK="${MASK:-land}"
if [[ "$MASK" != "land" && "$MASK" != "urban" ]]; then
  echo "ERROR: MASK must be 'land' or 'urban' (got '$MASK')" >&2
  exit 1
fi

module load python/3.11 mpi4py/4.0.3 esmf scipy-stack/2024a geos proj
source /home/vdemeyer/py3/bin/activate

# Build the task list (same order as the GLOST generator)
tasks=()
for sim in UBD UBE UBF; do
  for year in $(seq 1980 2014); do
    for q in 99 99.9; do
      tasks+=("$sim $year $q")
    done
  done
done
for sim in UBG UBH UBI; do
  for year in $(seq 2063 2097); do
    for q in 99 99.9; do
      tasks+=("$sim $year $q")
    done
  done
done

# Extract this task
read sim year quantile <<< "${tasks[$SLURM_ARRAY_TASK_ID]}"

echo "Array task $SLURM_ARRAY_TASK_ID : sim=$sim year=$year quantile=$quantile mask=$MASK"

python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/storm_percentile_metrics.py "$year" --sim "$sim" --quantile "$quantile" --mask "$MASK"

# Submit land mask:  sbatch --export=ALL,MASK=land  /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_storm_percentile_metrics.sh
# Submit urban mask: sbatch --export=ALL,MASK=urban /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_storm_percentile_metrics.sh
# Resubmit a subset: sbatch --export=ALL,MASK=urban --array=12,45,67 /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_storm_percentile_metrics.sh
