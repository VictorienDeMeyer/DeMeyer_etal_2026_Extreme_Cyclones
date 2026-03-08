#!/bin/bash

sims=(ERA5 UBB UBD UBE UBF UBG UBH UBI)
seasons=(ALL DJF MAM JJA SON)

for sim in "${sims[@]}"; do
    for season in "${seasons[@]}"; do
    
        time_limit="01:00:00"
        if [ "$season" = "ALL" ]; then
            time_limit="04:00:00"
        fi
        
        sbatch \
            --export=sim=$sim,season=$season \
            --job-name=${sim}_${season}_calculate_kde \
            --time=$time_limit \
            -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_${season}_calculate_kde.out" \
            /home/vdemeyer/TRACKING/KATJA/JOBS/calculate_kde.sh
    done
done

# . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_calculate_kde.sh