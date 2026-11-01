#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --time=03:00:00
#SBATCH --mem=48G
#SBATCH --job-name=significance_masks
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/significance_masks_%j.out

# Significance masks of the biases and projected changes (POSTPROCESSING/significance_masks.py).
# The density masks need the yearly densities first:
#   pairs_str="ERA5,YEARLY UBB,YEARLY UBD,YEARLY UBE,YEARLY UBF,YEARLY UBG,YEARLY UBH,YEARLY UBI,YEARLY" \
#     sbatch --array=0-7 --export=ALL,TC_FILTER=phase --time=06:00:00 --mem=12G /home/vdemeyer/TRACKING/KATJA/JOBS/calculate_kde.sh

# Optional TC_FILTER env var ('phase' or 'storm'): use the outputs without tropical cyclones
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

python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/significance_masks.py "${tc_arg[@]}"

# Submit: sbatch --export=ALL,TC_FILTER=phase /home/vdemeyer/TRACKING/KATJA/JOBS/submit_significance_masks.sh
