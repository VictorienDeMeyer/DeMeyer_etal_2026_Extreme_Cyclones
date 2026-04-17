#!/bin/bash

sims=("ERA5" "UBB" "UBD" "UBE" "UBF" "UBG" "UBH")

# Define the output file for GLOST tasks
glost_task_file="/home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/glost_tasks_EETCs_stat.txt"
> "$glost_task_file" # Clear the file if it exists


# Loop through each simulation
for sim in "${sims[@]}"; do
  if [[ "$sim" == "UBG" || "$sim" == "UBH" || "$sim" == "UBI" ]]; then
    start_year=2015 #mettre 2015 si on veut tout
    end_year=2100
  elif [ "$sim" == "UBB" ] || [ "$sim" == "ERA5" ]; then
    start_year=1979
    end_year=2023
  else
    start_year=1979
    end_year=2014
  fi

    # Loop over the range of years and submit a job for each year
    for iyear in $(seq $start_year $end_year); do

      output_dir="/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/EETC/${sim}/${iyear}"
      ## output_file="${output_dir}/EETC_cum_${sim}_Quebec_${iyear}_compound_8hrs_quantile_SSI_ref_ERA5.pkl"
      # output_file="${output_dir}/EETC_cum_${sim}_Quebec_1000hPa_${iyear}_compound_8hrs_quantile_SSI.pkl"
      # output_file="${output_dir}/EETC_cum_${sim}_Quebec_1000hPa_${iyear}_compound_8hrs_quantile_SSI_wetdays.pkl"
      # output_file="${output_dir}/EETC_cum_${sim}_Quebec_1000hPa_${iyear}_compound_8hrs_quantile_SSI_ratio.pkl"
      output_file="${output_dir}/dummy.pkl"
      
      if [ ! -f "$output_file" ]; then
        echo "python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/EETCs_stat.py $iyear --sim $sim --metric ratio" >> "$glost_task_file"
      else
        echo "Output file $output_file already exists. Skipping job submission for ${sim} ${iyear}."
      fi
    done
done

# . /home/vdemeyer/TRACKING/KATJA/JOBS/generate_tasks_EETCs_stat.sh