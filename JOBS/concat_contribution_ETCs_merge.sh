#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --time=00:12:00
#SBATCH --ntasks=1
#SBATCH --mem=40G
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null

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

python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/concat_contribution_ETCs.py --only-merge "${tc_arg[@]}"
