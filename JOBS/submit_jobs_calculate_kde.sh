#!/bin/bash

# Orchestrator: submits two job arrays to calculate_kde.sh.
#   - ALL season:    8 tasks (sims),                 4h
#   - Per-season:    8 x 4 = 32 tasks (sim,season),  1h

sims=(ERA5 UBB UBD UBE UBF UBG UBH UBI)
seasons=(DJF MAM JJA SON)

# ALL season (long time limit)
sims_str="${sims[*]}"
n_all=${#sims[@]}
sbatch --array=0-$((n_all-1)) \
       --export=sims_str="$sims_str",season=ALL \
       --job-name=ALL_calculate_kde \
       --time=04:00:00 \
       -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/%x_%a.out" \
       /home/vdemeyer/TRACKING/KATJA/JOBS/calculate_kde.sh

# Per-season (short time limit)
pairs=()
for sim in "${sims[@]}"; do
    for season in "${seasons[@]}"; do
        pairs+=("${sim},${season}")
    done
done
pairs_str="${pairs[*]}"
n=${#pairs[@]}
sbatch --array=0-$((n-1)) \
       --export=pairs_str="$pairs_str" \
       --job-name=calculate_kde \
       --time=01:00:00 \
       -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/%x_%a.out" \
       /home/vdemeyer/TRACKING/KATJA/JOBS/calculate_kde.sh

# . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_calculate_kde.sh
