#!/bin/bash

#Shell script to submit multiple jobs to the scheduler

# Define the simulations
sims=("UBB" "UBD" "UBE" "UBF" "UBG" "UBH" "UBI")
# sims=("ERA5")


# Loop through each simulation
for sim in "${sims[@]}"; do
  if [ "$sim" == "UBB" ]; then
    ranges=(
      "1979 1979"
      "1980 1989"
      "1990 1999"
      "2000 2009"
      "2010 2019"
      "2020 2023"
    )
  elif [[ "$sim" == "UBG" || "$sim" == "UBH" ]]; then
    ranges=(
      "2010 2019"
      "2020 2029"
      "2030 2039"
      "2040 2049"
      "2050 2059"
      "2060 2069"
      "2070 2079"
      "2080 2089"
      "2090 2099"
      "2100 2100"
    )
  elif [ "$sim" == "UBI" ]; then
    ranges=(
      "2010 2019"
      "2020 2029"
      "2030 2039"
      "2040 2049"
      "2050 2059"
      "2060 2069"
      "2070 2079"
      "2080 2089"
      "2090 2098"
    )
  else
    ranges=(
      "1979 1979"
      "1980 1989"
      "1990 1999"
      "2000 2009"
      "2010 2014"
    )
  fi

  # Loop through each range and submit the job
  for range in "${ranges[@]}"; do
    read -r start end <<< "$range"
    if [ "$range" == "1979 1979" ] || [ "$range" == "2100 2100" ]; then
      sbatch --mem=30G --time=00:10:00 --job-name=CRCM6_${sim}_psl_smooth_400km_12h_1005hPa_${start}-${end} -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/CRCM6_${sim}_psl_smooth_400km_12h_1005hPa_${start}-${end}.out" /home/vdemeyer/TRACKING/KATJA/JOBS/make_tracks_CRCM6.sh $range $sim
    elif [ "$range" == "2020 2023" ]; then
      sbatch --mem=90G --time=00:25:00 --job-name=CRCM6_${sim}_psl_smooth_400km_12h_1005hPa_${start}-${end} -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/CRCM6_${sim}_psl_smooth_400km_12h_1005hPa_${start}-${end}.out" /home/vdemeyer/TRACKING/KATJA/JOBS/make_tracks_CRCM6.sh $range $sim
    elif [ "$range" == "2010 2014" ]; then
      sbatch --mem=100G --time=00:30:00 --job-name=CRCM6_${sim}_psl_smooth_400km_12h_1005hPa_${start}-${end} -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/CRCM6_${sim}_psl_smooth_400km_12h_1005hPa_${start}-${end}.out" /home/vdemeyer/TRACKING/KATJA/JOBS/make_tracks_CRCM6.sh $range $sim
    else
      sbatch --job-name=CRCM6_${sim}_psl_smooth_400km_12h_1005hPa_${start}-${end} -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/CRCM6_${sim}_psl_smooth_400km_12h_1005hPa_${start}-${end}.out" /home/vdemeyer/TRACKING/KATJA/JOBS/make_tracks_CRCM6.sh $range $sim
    fi
  done
done

#. /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_make_tracks_CRCM6.sh