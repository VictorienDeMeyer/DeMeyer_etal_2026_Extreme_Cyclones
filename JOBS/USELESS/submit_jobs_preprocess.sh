#!/bin/bash

# sims=(UBB UBD UBE UBF UBG)
sims=(ERA5)

for sim in "${sims[@]}"; do
    sbatch --export=sim=$sim --job-name=${sim}_preprocess -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_preprocess.out" /home/vdemeyer/TRACKING/KATJA/JOBS/preprocess.sh
done

# . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_preprocess.sh