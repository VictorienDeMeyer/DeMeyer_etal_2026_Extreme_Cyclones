#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --time=03:00:00
#SBATCH --mem=96G
#SBATCH --job-name=IMERG_evaluation
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/IMERG_evaluation_%j.out

# Comparison of ERA5, CRCM6-ERA5 and IMERG over 2001-2014 (Sect. 3.1.2): runs the notebooks in place, with the py3
# kernel of JupyterLab, chosen with the STEP env var:
#   regrid  : POSTPROCESSING/regrid_IMERG_evaluation.ipynb (regridding onto the ERA5 grid and significance)
#   figures : PLOT/plot_map_IMERG_evaluation.ipynb (main and supplementary figures), after regrid
#   all     : both (default)
# Inputs: ALL/CONTRIB/contribution_ETCs_1000hPa_2001-2014_noTC.pkl (concat_contribution_ETCs.py --period 2001-2014).
# The executed notebooks keep their outputs and can be opened in JupyterLab (File -> Reload Notebook from Disk).

set -e
STEP="${STEP:-all}"
if [[ "$STEP" != "regrid" && "$STEP" != "figures" && "$STEP" != "all" ]]; then
  echo "ERROR: STEP must be regrid, figures or all (got '$STEP')" >&2
  exit 1
fi

# esmf is needed by xesmf and is not loaded by the kernel wrapper (python-wrapper.sh)
module load python/3.11 mpi4py/4.0.3 esmf scipy-stack/2024a geos proj
source /home/vdemeyer/py3/bin/activate

run() {
  echo "$(date '+%F %T') running $1"
  jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 \
    --ExecutePreprocessor.kernel_name=py3 "$1"
}

if [[ "$STEP" == "regrid" || "$STEP" == "all" ]]; then
  run /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/regrid_IMERG_evaluation.ipynb
fi
if [[ "$STEP" == "figures" || "$STEP" == "all" ]]; then
  run /home/vdemeyer/TRACKING/KATJA/PLOT/plot_map_IMERG_evaluation.ipynb
fi
echo "$(date '+%F %T') done"

# Submit: sbatch /home/vdemeyer/TRACKING/KATJA/JOBS/run_IMERG_evaluation.sh
#     or: sbatch --export=ALL,STEP=figures /home/vdemeyer/TRACKING/KATJA/JOBS/run_IMERG_evaluation.sh
