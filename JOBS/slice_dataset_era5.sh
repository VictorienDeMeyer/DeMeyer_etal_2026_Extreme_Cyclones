#!/bin/bash
#SBATCH --time=01:00:00
#SBATCH --account=rrg-gachon
#SBATCH --mem=120G
#SBATCH --ntasks=1
#SBATCH -o /home/vdemeyer/TRACKING/KATJA/JOBS/SLICE_ERA5.out
#SBATCH --job-name=SLICE_ERA5

cd /home/vdemeyer/TRACKING/KATJA/PREPROCESSING/

module load python/3.11 mpi4py/4.0.3 scipy-stack/2024a geos proj; source /home/vdemeyer/py3/bin/activate

mprof run -o /home/vdemeyer/TRACKING/KATJA/JOBS/RAM_stat_SLICE_ERA5.dat slice_dataset_era5.py

# sbatch /home/vdemeyer/TRACKING/KATJA/JOBS/slice_dataset_era5.sh