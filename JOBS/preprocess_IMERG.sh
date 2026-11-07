#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=48G
#SBATCH --job-name=preprocess_IMERG
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/preprocess_IMERG_%x_%A_%a.out

# Steps of PREPROCESSING/preprocess_IMERG.py, chosen with the STEP env var:
#   wait    : waits until the IMERG files of the period (and December of the previous year) are all there
#             and none of them changed for 10 minutes (end of the transfer)
#   mask    : CRCM6 domain mask on the IMERG grid
#   month   : hourly files, one array task per month of PERIOD (task 0 = January of the first year)
#   missing : map of the missing data over PERIOD
# PERIOD defaults to 2001-2014.

STEP="${STEP:?STEP must be wait, mask, month or missing}"
PERIOD="${PERIOD:-2001-2014}"
start=${PERIOD%-*}
end=${PERIOD#*-}

if [[ "$STEP" == "wait" ]]; then
  files=("/home/vdemeyer/projects/rrg-gachon/vdemeyer/IMERG/PR/$((start-1))/12/imerg_v7_precipitation_ll_$((start-1))12_30m.nc4")
  for year in $(seq $start $end); do
    for month in $(seq -w 1 12); do
      files+=("/home/vdemeyer/projects/rrg-gachon/vdemeyer/IMERG/PR/$year/$month/imerg_v7_precipitation_ll_$year${month}_30m.nc4")
    done
  done
  while true; do
    n=0
    for f in "${files[@]}"; do [[ -f "$f" ]] && n=$((n+1)); done
    echo "$(date '+%F %T') $n / ${#files[@]} files"
    if [[ $n -eq ${#files[@]} ]]; then
      before=$(stat -c '%s %Y' "${files[@]}" | md5sum)
      sleep 600
      after=$(stat -c '%s %Y' "${files[@]}" | md5sum)
      [[ "$before" == "$after" ]] && break
    else
      sleep 600
    fi
  done
  echo "All the files of $PERIOD are there"
  exit 0
fi

module load python/3.11 mpi4py/4.0.3 scipy-stack/2024a geos proj
source /home/vdemeyer/py3/bin/activate

if [[ "$STEP" == "month" ]]; then
  year=$((start + SLURM_ARRAY_TASK_ID / 12))
  month=$((SLURM_ARRAY_TASK_ID % 12 + 1))
  python /home/vdemeyer/TRACKING/KATJA/PREPROCESSING/preprocess_IMERG.py month --year $year --month $month
else
  python /home/vdemeyer/TRACKING/KATJA/PREPROCESSING/preprocess_IMERG.py $STEP --period $PERIOD
fi

# Chain (see SUIVI_TC_EXCLUSION.md, section 8):
#   sbatch --export=ALL,STEP=mask /home/vdemeyer/TRACKING/KATJA/JOBS/preprocess_IMERG.sh
#   sbatch --export=ALL,STEP=wait --time=12:00:00 --mem=1G /home/vdemeyer/TRACKING/KATJA/JOBS/preprocess_IMERG.sh
#   sbatch --export=ALL,STEP=month --array=0-167 --time=01:00:00 --dependency=afterok:<wait>:<mask> /home/vdemeyer/TRACKING/KATJA/JOBS/preprocess_IMERG.sh
#   sbatch --export=ALL,STEP=missing --mem=8G --dependency=afterok:<month> /home/vdemeyer/TRACKING/KATJA/JOBS/preprocess_IMERG.sh
