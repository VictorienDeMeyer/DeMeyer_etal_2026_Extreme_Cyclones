#!/bin/bash

#Shell script to submit multiple jobs to the scheduler

# Define the simulations
sims=("UBB" "UBD" "UBE" "UBF" "UBG" "UBH" "UBI")

# Loop through each simulation
for sim in "${sims[@]}"; do

  if [[ "$sim" == "UBG" || "$sim" == "UBH" ]]; then
      start_year=2015
      end_year=2100
  elif [ "$sim" == "UBI" ]; then
      start_year=2015
      end_year=2098
  elif [ "$sim" == "UBB" ] || [ "$sim" == "ERA5" ]; then
      start_year=1979
      end_year=2023
  else
      start_year=1979
      end_year=2014
  fi

  for year in $(seq $start_year $end_year); do
    sbatch --job-name=${sim}_psl_smooth_400km_12h_1000hPa_${year} -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_psl_smooth_400km_12h_1000hPa_${year}.out" /home/vdemeyer/TRACKING/KATJA/JOBS/make_tracks_CRCM6.sh $year $sim
  done

done

#. /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_make_tracks_CRCM6.sh