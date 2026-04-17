# !/bin/bash

# sims=("ERA5" "UBB" "UBD" "UBE" "UBF" "UBG" "UBH" "UBI")

sims=("ERA5" "UBB")

# Loop through each simulation
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

    # Loop over the range of years and submit a job for each year
    for iyear in $(seq $start_year $end_year); do

      sbatch --export=iyear=$iyear,sim=$sim --job-name=${sim}_${iyear}_ETCs_1000km -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_${iyear}_ETCs_1000km.out" /home/vdemeyer/TRACKING/KATJA/JOBS/ETCs_1000km.sh

    done
done

# sims=("UBH")
# single_year=2098  # Specify the year you want to submit

# # Loop through each simulation
# for sim in "${sims[@]}"; do
#   # Submit a job for the specified year
#   sbatch --export=iyear=$single_year,sim=$sim --job-name=${sim}_${single_year}_ETCs_1000km -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_${single_year}_ETCs_1000km.out" /home/vdemeyer/TRACKING/KATJA/JOBS/ETCs_1000km.sh
# done


# . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_ETCs_1000km.sh