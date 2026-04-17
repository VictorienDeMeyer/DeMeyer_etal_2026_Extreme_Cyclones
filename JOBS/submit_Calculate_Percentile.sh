#!/bin/bash

for sim in ERA5 UBB UBD UBE UBF UBG UBH UBI; do
    for variable in Precipitation Wind; do
        if [ "$variable" = "Wind" ]; then
            mem="260G"
        else
            mem="220G"
        fi
        sbatch --mem=$mem --export=sim=$sim,variable=$variable --job-name=${sim}_${variable}_percentile /home/vdemeyer/TRACKING/KATJA/JOBS/Calculate_Percentile.sh
    done
done

# . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_Calculate_Percentile.sh