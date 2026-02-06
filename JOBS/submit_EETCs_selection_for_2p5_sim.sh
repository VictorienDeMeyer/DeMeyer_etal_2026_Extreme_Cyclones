#!/bin/bash

# sims=("ERA5" "UBB" "UBD" "UBE" "UBF")
sims=("UBI")

for sim in "${sims[@]}"; do
    sbatch --export=sim=$sim --job-name=${sim}_EETCs_selection_for_2p5_sim -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_EETCs_selection_for_2p5_sim.out" /home/vdemeyer/TRACKING/KATJA/JOBS/EETCs_selection_for_2p5_sim.sh
done

# . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_EETCs_selection_for_2p5_sim.sh