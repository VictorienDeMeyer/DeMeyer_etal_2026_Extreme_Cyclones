#!/bin/bash

start_year=1979
end_year=2023

for year in $(seq $start_year $end_year); do

    sbatch --export=year=$year --job-name=ERA5_${year}_slice_yearly -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/ERA5_${year}_slice.out" /home/vdemeyer/TRACKING/KATJA/JOBS/slice_yearly_ERA5.sh

done

# . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_slice_yearly_ERA5.sh