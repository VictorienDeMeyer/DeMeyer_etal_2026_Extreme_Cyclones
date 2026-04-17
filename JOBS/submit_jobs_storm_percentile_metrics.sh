#!/bin/bash

# sims=("ERA5" "UBB" "UBD" "UBE" "UBF" "UBG" "UBH" "UBI")

sims=("UBD" "UBE" "UBF" "UBG" "UBH" "UBI")

for sim in "${sims[@]}"; do

  case "$sim" in
    ERA5|UBB|UBD|UBE|UBF)
      start_year=1980
      end_year=2014
      ;;

    UBG|UBH|UBI)
      start_year=2063
      end_year=2097
      ;;
  esac

  for iyear in $(seq $start_year $end_year); do
    sbatch --export=iyear=$iyear,sim=$sim \
           --job-name=${sim}_${iyear}_storm_metrics \
           -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_${iyear}_storm_percentile_metrics.out" \
           /home/vdemeyer/TRACKING/KATJA/JOBS/storm_percentile_metrics.sh
  done
done

# . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_storm_percentile_metrics.sh
