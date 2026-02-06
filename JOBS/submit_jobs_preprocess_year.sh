#!/bin/bash

sims=("ERA5" "UBB" "UBD" "UBE" "UBF" "UBG" "UBH" "UBI")

# Loop through each simulation
for sim in "${sims[@]}"; do

    if [[ "$sim" == "UBG" || "$sim" == "UBH" ]]; then
        start_year=2014
        end_year=2100
    elif [ "$sim" == "UBI" ]; then
        start_year=2014
        end_year=2098
    elif [ "$sim" == "UBB" ] || [ "$sim" == "ERA5" ]; then
        start_year=1979
        end_year=2023
    else
        start_year=1979
        end_year=2014
    fi

    # Loop over the range of years and submit a job for each year
    for year in $(seq $start_year $end_year); do

        output_dir="/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/INPUTS/${sim}"
        output_file="${output_dir}/dummy.pkl"
      
        if [ ! -f "$output_file" ]; then
            sbatch --export=year=$year,sim=$sim --job-name=${sim}_${year}_preprocess -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_${year}_preprocess.out" /home/vdemeyer/TRACKING/KATJA/JOBS/preprocess_year.sh
        else
            echo "Output file $output_file already exists. Skipping job submission for ${sim} ${year}."
        fi

    done
done

# single_year=2098  # Specify the year you want to submit

# # Loop through each simulation
# for sim in "${sims[@]}"; do
#   # Submit a job for the specified year
#   sbatch --export=iyear=$single_year,sim=$sim --job-name=${sim}_${single_year}_EETCs_stat -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_${single_year}_preprocess.out" /home/vdemeyer/TRACKING/KATJA/JOBS/preprocess_year.sh
# done

# . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_preprocess_year.sh