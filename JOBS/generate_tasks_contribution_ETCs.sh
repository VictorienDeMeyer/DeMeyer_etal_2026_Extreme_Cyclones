#!/bin/bash

sims=("ERA5" "UBB" "UBD" "UBE" "UBF" "UBG" "UBH")
vars=("pr" "ws")

glost_task_file_EETCs="/home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/glost_tasks_contribution_ETCs.txt"
> "$glost_task_file_EETCs"

# Loop through each simulation
for sim in "${sims[@]}"; do
  if [[ "$sim" == "UBG" || "$sim" == "UBH" || "$sim" == "UBI" ]]; then
    start_year=2065 #mettre 2015 si on veut tout
    end_year=2100
  elif [ "$sim" == "UBB" ] || [ "$sim" == "ERA5" ]; then
    start_year=1979
    end_year=2023
  else
    start_year=1979
    end_year=2014
  fi

  for var in "${vars[@]}"; do
    for iyear in $(seq $start_year $end_year); do
      echo "python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/contribution_ETCs.py $iyear --sim $sim --var $var" >> "$glost_task_file_EETCs"
    done
  done
done

# . /home/vdemeyer/TRACKING/KATJA/JOBS/generate_tasks_contribution_ETCs.sh