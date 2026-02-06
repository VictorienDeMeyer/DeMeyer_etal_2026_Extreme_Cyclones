# !/bin/bash

sims=("ERA5" "UBB" "UBD" "UBE" "UBF" "UBG" "UBH" "UBI")

# Loop through each simulation
for sim in "${sims[@]}"; do
  if [[ "$sim" == "UBG" || "$sim" == "UBH" ]]; then
    start_year=2058 #mettre 2015 si on veut tout
    end_year=2100
  elif [ "$sim" == "UBI" ]; then
    start_year=2058 #mettre 2015 si on veut tout
    end_year=2098
  elif [ "$sim" == "UBB" ] || [ "$sim" == "ERA5" ]; then
    start_year=1979
    end_year=2023
  else
    start_year=1979
    end_year=2014
  fi

    # Loop over the range of years and submit a job for each year
    for iyear in $(seq $start_year $end_year); do

      output_dir="/home/vdemeyer/projects/rrg-gachon/vdemeyer/${sim}/WIND/"
      if [ "$sim" == "ERA5" ]; then
        output_dir="${output_dir}Magnitude/"
      fi
      output_dir="${output_dir}1000km_storm/"
      output_file_ETCs="${output_dir}/wind10_${sim,,}_${iyear}12_1000km_1005hPa_storm.nc" #december for ERA5 is dumb since it stops in august
      output_file_EETCs="${output_dir}/wind10_${sim,,}_${iyear}12_1000km_1005hPa_extreme_storm_wetdays.nc"
      
      # if [ ! -f "$output_file_ETCs" ]; then
      sbatch --export=iyear=$iyear,sim=$sim --job-name=${sim}_${iyear}_ETCs_1000km -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_${iyear}_ETCs_1000km.out" /home/vdemeyer/TRACKING/KATJA/JOBS/ETCs_1000km.sh
      # else
      #   echo "Output file $output_file_ETCs already exists. Skipping job submission for ${sim} ${iyear}."
      # if [ ! -f "$output_file_EETCs" ]; then
      sbatch --export=iyear=$iyear,sim=$sim --job-name=${sim}_${iyear}_EETCs_1000km -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_${iyear}_EETCs_1000km.out" /home/vdemeyer/TRACKING/KATJA/JOBS/EETCs_1000km.sh
      # else
        # echo "Output file $output_file_EETCs already exists. Skipping job submission for ${sim} ${iyear}."
      # fi
    done
done

# sims=("UBD")
# single_year=1984  # Specify the year you want to submit

# # Loop through each simulation
# for sim in "${sims[@]}"; do
#   # Submit a job for the specified year
#   sbatch --export=iyear=$single_year,sim=$sim --job-name=${sim}_${single_year}_ETCs_1000km -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_${single_year}_ETCs_1000km.out" /home/vdemeyer/TRACKING/KATJA/JOBS/ETCs_1000km.sh
#   # sbatch --export=iyear=$single_year,sim=$sim --job-name=${sim}_${single_year}_EETCs_1000km -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_${single_year}_EETCs_1000km.out" /home/vdemeyer/TRACKING/KATJA/JOBS/EETCs_1000km.sh
# done


# . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_ETCs_1000km.sh