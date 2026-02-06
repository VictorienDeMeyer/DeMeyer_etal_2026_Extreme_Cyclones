#!/bin/bash

#Shell script to submit multiple jobs to the scheduler

# Define the ranges
ranges=(
  "1979 1979"
  "1980 1989"
  "1990 1999"
  "2000 2009"
  "2010 2019"
  "2020 2023"
)

# Loop through each range and submit the job
for range in "${ranges[@]}"; do
  read -r start end <<< "$range"
  if [ "$range" == "1979 1979" ]; then
    sbatch --mem=115G --time=00:06:00 --job-name=ERA5_CORDEX_NA_psl_smooth_400km_12h_1005hPa_${start}-${end} -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/ERA5_CORDEX_NA_psl_smooth_400km_12h_1005hPa_${start}-${end}.out" /home/vdemeyer/TRACKING/KATJA/JOBS/make_tracks_ERA5.sh $range
  elif [ "$range" == "2020 2023" ]; then
    sbatch --mem=140G --time=02:30:00 --job-name=ERA5_CORDEX_NA_psl_smooth_400km_12h_1005hPa_${start}-${end} -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/ERA5_CORDEX_NA_psl_smooth_400km_12h_1005hPa_${start}-${end}.out" /home/vdemeyer/TRACKING/KATJA/JOBS/make_tracks_ERA5.sh $range
  else
    sbatch --job-name=ERA5_CORDEX_NA_psl_smooth_400km_12h_1005hPa_${start}-${end} -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/ERA5_CORDEX_NA_psl_smooth_400km_12h_1005hPa_${start}-${end}.out" /home/vdemeyer/TRACKING/KATJA/JOBS/make_tracks_ERA5.sh $range
  fi
  echo "for range: $range"
  echo ""
done

#. /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_make_tracks_ERA5.sh