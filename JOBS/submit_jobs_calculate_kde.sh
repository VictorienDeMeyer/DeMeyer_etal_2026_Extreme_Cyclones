#!/bin/bash

sims=(ERA5 UBI UBB UBD UBE UBF UBG UBH)
# sims=(ERA5)
seasons=(ALL DJF MAM JJA SON)

for sim in "${sims[@]}"; do
    for season in "${seasons[@]}"; do
        sbatch \
            --export=sim=$sim,season=$season \
            --job-name=${sim}_${season}_calculate_kde \
            -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_${season}_calculate_kde.out" \
            /home/vdemeyer/TRACKING/KATJA/JOBS/calculate_kde.sh
    done
done

# . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_calculate_kde.sh