#!/bin/bash
#SBATCH --account=rrg-gachon
#SBATCH --time=00:30:00
#SBATCH --mem=32G
#SBATCH --job-name=plot_map_ETCs_RCM_vs_driving
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/plot_map_ETCs_RCM_vs_driving_%j.out

# Share of the RCM and of the driving data in the biases of Figs. 3 and 5: maps and tables
# (PLOT/plot_map_ETCs_RCM_vs_driving.py). The tropical cyclone filter is the one set at the top of the figure
# notebooks (tc_filter = 'phase': _noTC).

module load python/3.11 mpi4py/4.0.3 esmf scipy-stack/2024a geos proj
source /home/vdemeyer/py3/bin/activate

python /home/vdemeyer/TRACKING/KATJA/PLOT/plot_map_ETCs_RCM_vs_driving.py

# Submit: sbatch /home/vdemeyer/TRACKING/KATJA/JOBS/plot_map_ETCs_RCM_vs_driving.sh
