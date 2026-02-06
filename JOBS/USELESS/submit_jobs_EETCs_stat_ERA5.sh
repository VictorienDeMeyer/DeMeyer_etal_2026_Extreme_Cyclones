#!/bin/bash

# start_year=1979
# end_year=2023

# # Loop over the range of years and submit a job for each year
# for iyear in $(seq $start_year $end_year); do
#     sbatch --export=iyear=$iyear /home/vdemeyer/TRACKING/KATJA/JOBS/EETCs_stat.sh
# done

years=(1979 2017 2020)

# Loop over the specified years and submit a job for each year
for iyear in "${years[@]}"; do
    sbatch --export=iyear=$iyear /home/vdemeyer/TRACKING/KATJA/JOBS/EETCs_stat.sh
done

# bash /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_EETCs_stat.sh