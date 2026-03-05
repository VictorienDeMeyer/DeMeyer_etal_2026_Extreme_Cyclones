#!/bin/bash

# sims=(UBB UBD UBE UBF UBG)
sims=(UBG UBH UBI)

for sim in "${sims[@]}"; do
    sbatch --export=sim=$sim --job-name=${sim}_WIND -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_wind_magnitude.out" /home/vdemeyer/TRACKING/KATJA/JOBS/Calculate_Wind_Magnitude.sh
done

# . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_Calculate_Wind_Magnitude.sh