#!/bin/bash

iyear=$1
sim=$2
quantile=$3

module load python/3.11 mpi4py/4.0.3 esmf scipy-stack/2024a geos proj; source /home/vdemeyer/py3/bin/activate

python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/storm_percentile_metrics.py $iyear --sim $sim --quantile $quantile
