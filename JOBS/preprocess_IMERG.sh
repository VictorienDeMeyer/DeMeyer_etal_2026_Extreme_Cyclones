#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=48G
#SBATCH --job-name=preprocess_IMERG
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/preprocess_IMERG_%x_%A_%a.out

# Steps of PREPROCESSING/preprocess_IMERG.py, chosen with the STEP env var:
#   mask    : CRCM6 domain mask on the IMERG grid
#   month   : hourly files, one array task per month of PERIOD (task 0 = January of the first year)
#   missing : map of the missing data over PERIOD
# PERIOD defaults to 2001-2014.

STEP="${STEP:?STEP must be mask, month or missing}"
PERIOD="${PERIOD:-2001-2014}"
start=${PERIOD%-*}
end=${PERIOD#*-}

module load python/3.11 mpi4py/4.0.3 scipy-stack/2024a geos proj
source /home/vdemeyer/py3/bin/activate

if [[ "$STEP" == "month" ]]; then
  year=$((start + SLURM_ARRAY_TASK_ID / 12))
  month=$((SLURM_ARRAY_TASK_ID % 12 + 1))
  python /home/vdemeyer/TRACKING/KATJA/PREPROCESSING/preprocess_IMERG.py month --year $year --month $month
else
  python /home/vdemeyer/TRACKING/KATJA/PREPROCESSING/preprocess_IMERG.py $STEP --period $PERIOD
fi

# Chain (the raw half-hourly files IMERG/PR/YYYY/MM/*.nc4, December 2000 included, are on the server):
#   sbatch --export=ALL,STEP=mask /home/vdemeyer/TRACKING/KATJA/JOBS/preprocess_IMERG.sh
#   sbatch --export=ALL,STEP=month --array=0-167 --time=01:00:00 --dependency=afterok:<mask> /home/vdemeyer/TRACKING/KATJA/JOBS/preprocess_IMERG.sh
#   sbatch --export=ALL,STEP=missing --mem=8G --dependency=afterok:<month> /home/vdemeyer/TRACKING/KATJA/JOBS/preprocess_IMERG.sh
