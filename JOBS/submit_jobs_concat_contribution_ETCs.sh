#!/bin/bash

# Orchestrator: submits the per-sim calc array, then the merge job (afterok).

sims=("ERA5" "UBB" "UBD" "UBE" "UBF" "UBG" "UBH" "UBI")
sims_str="${sims[*]}"
last=$((${#sims[@]}-1))

jobid=$(sbatch --parsable \
               --array=0-${last} \
               --export=sims_str="$sims_str" \
               --job-name=concat_contrib \
               /home/vdemeyer/TRACKING/KATJA/JOBS/concat_contribution_ETCs_calc.sh)

sbatch --dependency=afterok:$jobid \
       --job-name=All_concat_contrib \
       /home/vdemeyer/TRACKING/KATJA/JOBS/concat_contribution_ETCs_merge.sh

# . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_concat_contribution_ETCs.sh
