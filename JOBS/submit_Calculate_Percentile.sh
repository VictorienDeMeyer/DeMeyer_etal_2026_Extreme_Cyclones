#!/bin/bash

for sim in ERA5; do
    for variable in Precipitation; do
        if [ "$variable" = "Wind" ]; then
            mem="550G"
        else
            mem="500G"
        fi
        sbatch --mem=$mem --export=sim=$sim,variable=$variable --job-name=${sim}_${variable}_percentile /home/vdemeyer/TRACKING/KATJA/JOBS/Calculate_Percentile.sh
    done
done

# . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_Calculate_Percentile.sh