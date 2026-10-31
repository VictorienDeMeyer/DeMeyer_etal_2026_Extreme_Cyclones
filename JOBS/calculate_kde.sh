#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --ntasks=1
#SBATCH --mem=6G

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

python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/calculate_kde.py $sim $season "${tc_arg[@]}"
