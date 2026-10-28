#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --array=0-7
#SBATCH --job-name=classify_cyclone_phase
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/classify_cyclone_phase_%A_%a.out

# Label each time step of each tracked cyclone as TC / TRANSITION / ETC (one task per sim).
# Requires all the outputs of submit_jobs_cyclone_phase_space.sh.
# For ERA5 and UBB, the labels are then evaluated against IBTrACS if the IBTrACS csv files
# are available (see POSTPROCESSING/validate_phase_ibtracs.py).

module load python/3.11 mpi4py/4.0.3 esmf scipy-stack/2024a geos proj
source /home/vdemeyer/py3/bin/activate

sims=(ERA5 UBB UBD UBE UBF UBG UBH UBI)
sim=${sims[$SLURM_ARRAY_TASK_ID]}

echo "Array task $SLURM_ARRAY_TASK_ID : sim=$sim"

python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/classify_cyclone_phase.py --sim "$sim" || exit 1

if [[ "$sim" == "ERA5" || "$sim" == "UBB" ]]; then
  if ls /home/vdemeyer/projects/rrg-gachon/vdemeyer/ALL/IBTRACS/ibtracs.*.list.v04r01.csv >/dev/null 2>&1; then
    python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/validate_phase_ibtracs.py --sim "$sim"
  else
    echo "No IBTrACS files in /home/vdemeyer/projects/rrg-gachon/vdemeyer/ALL/IBTRACS: validation skipped"
  fi
fi

# Submit: sbatch /home/vdemeyer/TRACKING/KATJA/JOBS/submit_classify_cyclone_phase.sh
# Or after the CPS jobs: sbatch --dependency=afterok:<jobid> /home/vdemeyer/TRACKING/KATJA/JOBS/submit_classify_cyclone_phase.sh
