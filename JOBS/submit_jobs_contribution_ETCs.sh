#!/bin/bash

# sims=("ERA5" "UBB" "UBD" "UBE" "UBF" "UBG" "UBH" "UBI")
# sims=("ERA5")
# vars=("pr" "ws")

# # Loop through each simulation
# for sim in "${sims[@]}"; do
#   if [[ "$sim" == "UBG" || "$sim" == "UBH" ]]; then
#     start_year=2058 #mettre 2015 si on veut tout
#     end_year=2100
#   elif [ "$sim" == "UBI" ]; then
#     start_year=2058 #mettre 2015 si on veut tout
#     end_year=2098
#   elif [ "$sim" == "UBB" ] || [ "$sim" == "ERA5" ]; then
#     start_year=1979
#     end_year=2023
#   else
#     start_year=1979
#     end_year=2014
#   fi

#   for var in "${vars[@]}"; do
#     for iyear in $(seq $start_year $end_year); do

#       sbatch --export=iyear=$iyear,sim=$sim,var=$var --job-name=${sim}_${iyear}_${var}_ETCs_contrib -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_${iyear}_${var}_ETCs_contrib.out" /home/vdemeyer/TRACKING/KATJA/JOBS/contribution_ETCs.sh

#     done
#   done
# done

sims=("UBH")
vars=("ws")
single_year=2066  # Specify the year you want to submit
# Loop through each simulation
for sim in "${sims[@]}"; do
  # Submit a job for the specified year
  for var in "${vars[@]}"; do
    sbatch --export=iyear=$single_year,sim=$sim,var=$var --job-name=${sim}_${single_year}_${var}_ETCs_contrib -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_${single_year}_${var}_ETCs_contrib.out" /home/vdemeyer/TRACKING/KATJA/JOBS/contribution_ETCs.sh
  done
done


# . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_contribution_ETCs.sh