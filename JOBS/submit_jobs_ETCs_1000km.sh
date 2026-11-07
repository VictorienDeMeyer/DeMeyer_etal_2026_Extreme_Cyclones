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

# Optional TC_FILTER env var ('phase' or 'storm'): exclude the tropical cyclones
# (see POSTPROCESSING/ETC_tools.py). If unset/empty, all tracked cyclones are used.
TC_FILTER="${TC_FILTER:-}"
if [[ -n "$TC_FILTER" && "$TC_FILTER" != "phase" && "$TC_FILTER" != "storm" ]]; then
  echo "ERROR: TC_FILTER must be empty or 'phase' or 'storm' (got '$TC_FILTER')" >&2
  exit 1
fi
tc_arg=()
if [[ -n "$TC_FILTER" ]]; then
  tc_arg=(--tc_filter "$TC_FILTER")
fi

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

# Optional PERIOD and SIMS env vars (e.g. PERIOD=2001-2014 SIMS=IMERG with --array=0-13):
# one task per sim and year of the period instead of the list above
if [[ -n "${PERIOD:-}" ]]; then
  tasks=()
  for sim in ${SIMS:?SIMS is needed with PERIOD}; do
    for year in $(seq ${PERIOD%-*} ${PERIOD#*-}); do
      tasks+=("$sim $year")
    done
  done
fi

read sim year <<< "${tasks[$SLURM_ARRAY_TASK_ID]}"

echo "Array task $SLURM_ARRAY_TASK_ID : sim=$sim year=$year tc_filter=${TC_FILTER:-<none>}"

python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/ETCs_1000km.py "$year" --sim "$sim" "${tc_arg[@]}"

# Submit: sbatch /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_ETCs_1000km.sh
# Submit without tropical cyclones: sbatch --export=ALL,TC_FILTER=phase /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_ETCs_1000km.sh
# Resubmit a subset: sbatch --array=12,45,67 /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_ETCs_1000km.sh
# IMERG (ERA5 tracks, IMERG grid): sbatch --array=0-13 --time=10:00:00 --mem=32G --export=ALL,TC_FILTER=phase,PERIOD=2001-2014,SIMS=IMERG /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_ETCs_1000km.sh
