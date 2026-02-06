#!/bin/bash

#Shell script to submit multiple jobs to the scheduler

start_year=2019
end_year=2019

for year in $(seq $start_year $end_year); do
  sbatch --job-name=ERA5_CORDEX_NA_psl_smooth_400km_12h_1005hPa_${year} -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/ERA5_CORDEX_NA_psl_smooth_400km_12h_1005hPa_${year}.out" /home/vdemeyer/TRACKING/KATJA/JOBS/make_tracks_ERA5.sh $year
done

#. /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_make_tracks_ERA5.sh