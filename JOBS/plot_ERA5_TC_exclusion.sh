#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --job-name=plot_ERA5_TC_exclusion
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/plot_ERA5_TC_exclusion_%j.out

# Figures of the ERA5 test of the tropical cyclone exclusion (PLOT/plot_ERA5_TC_exclusion.py)

module load python/3.11 mpi4py/4.0.3 esmf scipy-stack/2024a geos proj
source /home/vdemeyer/py3/bin/activate

for fig in validation cps ee density; do
  python /home/vdemeyer/TRACKING/KATJA/PLOT/plot_ERA5_TC_exclusion.py --fig $fig
done
