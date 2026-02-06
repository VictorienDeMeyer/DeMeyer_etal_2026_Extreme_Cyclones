#!/bin/bash

sims=("ERA5" "UBB" "UBD" "UBE" "UBF" "UBG" "UBH" "UBI")

job_ids=()
for sim in "${sims[@]}"; do
    jobid=$(sbatch --parsable --export=sim=$sim --job-name=${sim}_concat_contrib /home/vdemeyer/TRACKING/KATJA/JOBS/concat_contribution_ETCs_calc.sh)
    job_ids+=($jobid)
done

# Create dependency string
dep_str=$(IFS=:; echo "${job_ids[*]}")

sbatch --job-name=All_concat_contrib --dependency=afterok:$dep_str /home/vdemeyer/TRACKING/KATJA/JOBS/concat_contribution_ETCs_merge.sh

# . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_concat_contribution_ETCs.sh