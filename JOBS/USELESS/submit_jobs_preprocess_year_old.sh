#!/bin/bash

# sims=("ERA5" "UBB" "UBD" "UBE" "UBF" "UBG" "UBH" "UBI")
sims=("ERA5")

# Loop through each simulation
for sim in "${sims[@]}"; do

    if [[ "$sim" == "UBG" || "$sim" == "UBH" ]]; then
        start_year=2014
        end_year=2100
        range=(2010 2020 2030 2040 2050 2060 2070 2080 2090 2100)
    elif [ "$sim" == "UBI" ]; then
        start_year=2014
        end_year=2098
        range=(2010 2020 2030 2040 2050 2060 2070 2080 2090 2098)
    elif [ "$sim" == "UBB" ] || [ "$sim" == "ERA5" ]; then
        # start_year=1979
        # end_year=2023
        start_year=1999
        end_year=1999
        range=(1990 2000)
    else
        start_year=1979
        end_year=2014
        range=(1979 1980 1990 2000 2010 2014)
    fi

    # Loop over the range of years and submit a job for each year
    job_ids=()
    for year in $(seq $start_year $end_year); do

        output_dir="/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/INPUTS/${sim}"
        # output_file="${output_dir}/${sim}_psl_smoothed_400km_${year}_pres.pkl"
        output_file="${output_dir}/dummy.pkl"
      
        if [ ! -f "$output_file" ]; then
            if [ "$sim" != "ERA5" ]; then
                jobid=$(sbatch --parsable --export=year=$year,sim=$sim --job-name=${sim}_${year}_preprocess -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_${year}_preprocess.out" /home/vdemeyer/TRACKING/KATJA/JOBS/preprocess_year.sh)
                job_ids+=($jobid)
            else
                sbatch --export=year=$year,sim=$sim --job-name=${sim}_${year}_preprocess -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_${year}_preprocess.out" /home/vdemeyer/TRACKING/KATJA/JOBS/preprocess_year.sh
            fi
        else
            echo "Output file $output_file already exists. Skipping job submission for ${sim} ${year}."
        fi

    done

    if [ "$sim" != "ERA5" ]; then
        dep_str=$(IFS=:; echo "${job_ids[*]}")
        for i in "${!range[@]}"; do
            if [ $i -eq 0 ]; then
                continue
            fi
            start_year=${range[$((i-1))]}
            end_year=${range[$i]}
            printf "Submitting decade preprocessing job for %s from %d to %d\n" "$sim" "$start_year" "$end_year"
            # sbatch --export=sim=$sim,start_year=$start_year,end_year=$end_year --job-name=${sim}_${start_year}_${end_year}_slice_decade_preprocess --dependency=afterok:$dep_str -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_${start_year}_${end_year}_slice_decade_preprocess.out" /home/vdemeyer/TRACKING/KATJA/JOBS/slice_decade_preprocess.sh
            sbatch --export=sim=$sim,start_year=$start_year,end_year=$end_year --job-name=${sim}_${start_year}_${end_year}_slice_decade_preprocess -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_${start_year}_${end_year}_slice_decade_preprocess.out" /home/vdemeyer/TRACKING/KATJA/JOBS/slice_decade_preprocess.sh
        done
    fi
done

# single_year=2098  # Specify the year you want to submit

# # Loop through each simulation
# for sim in "${sims[@]}"; do
#   # Submit a job for the specified year
#   sbatch --export=iyear=$single_year,sim=$sim --job-name=${sim}_${single_year}_EETCs_stat -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_${single_year}_preprocess.out" /home/vdemeyer/TRACKING/KATJA/JOBS/preprocess_year.sh
# done

# . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_preprocess_year.sh