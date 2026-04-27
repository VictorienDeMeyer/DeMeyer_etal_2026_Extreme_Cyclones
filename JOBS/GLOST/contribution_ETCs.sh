#!/bin/bash

iyear=$1
sim=$2
var=$3

module load python/3.11 mpi4py/4.0.3 scipy-stack/2024a geos proj; source /home/vdemeyer/py3/bin/activate

python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/contribution_ETCs.py $iyear --sim $sim --var $var