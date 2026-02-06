#!/bin/bash

# sims=("ERA5" "UBB" "UBD" "UBE" "UBF")
sims=("UBB" "UBD" "UBE" "UBF")
# sims=("UBB")
vars=("pr" "ws")
# vars=("pr")

for var in "${vars[@]}"; do
  for sim in "${sims[@]}"; do
    # sbatch --export=sim=$sim,var=$var --job-name=${sim}_${var}_ETCs_contrib -o "/home/vdemeyer/projects/rrg-gachon/vdemeyer/JOB_OUTPUT/${sim}_${var}_ETCs_contrib.out" /home/vdemeyer/TRACKING/KATJA/JOBS/contribution_ETCs.sh
    # sbatch --export=sim=$sim,var=$var --job-name=${sim}_${var}_EETCs_contrib -o "/home/vdemeyer/projects/rrg-gachon/vdemeyer/JOB_OUTPUT/${sim}_${var}_EETCs_contrib.out" /home/vdemeyer/TRACKING/KATJA/JOBS/contribution_EETCs.sh
    sbatch --export=sim=$sim,var=$var --job-name=${sim}_${var}_EETCs_contrib_ext -o "/home/vdemeyer/projects/rrg-gachon/vdemeyer/JOB_OUTPUT/${sim}_${var}_EETCs_contrib_ext.out" /home/vdemeyer/TRACKING/KATJA/JOBS/contribution_ext_EETCs.sh
  done
done

# . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_contribution_ETCs.sh