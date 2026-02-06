#!/bin/bash

sims=("ERA5" "UBB" "UBD" "UBE" "UBF" "UBG" "UBH")

# Fichier de tâches GLOST pour ETCs et EETCs
# glost_task_file_ETCs="/home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/glost_tasks_ETCs_1000km.txt"
glost_task_file_EETCs="/home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/glost_tasks_EETCs_1000km.txt"
# > "$glost_task_file_ETCs"
> "$glost_task_file_EETCs"

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

  for iyear in $(seq $start_year $end_year); do
    output_dir="/home/vdemeyer/projects/rrg-gachon/vdemeyer/${sim}/WIND/"
    if [ "$sim" == "ERA5" ]; then
      output_dir="${output_dir}Magnitude/"
    fi
    output_dir="${output_dir}1000km_storm/"

    if [ "$iyear" -eq 2023 ] && [ "$sim" == "ERA5" ]; then
      # output_file_ETCs="${output_dir}/wind10_${sim,,}_${iyear}08_1000km_1005hPa_storm.nc"
      # output_file_EETCs="${output_dir}/wind10_${sim,,}_${iyear}08_1000km_1005hPa_extreme_storm_wetdays.nc"
      output_file_EETCs="dummy.nc"
    else
      # output_file_ETCs="${output_dir}/wind10_${sim,,}_${iyear}12_1000km_1005hPa_storm.nc"
      # output_file_EETCs="${output_dir}/wind10_${sim,,}_${iyear}12_1000km_1005hPa_extreme_storm_wetdays.nc"
      output_file_EETCs="dummy.nc"
    fi

    # if [ ! -f "$output_file_ETCs" ]; then
      # echo "python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/ETCs_1000km.py $iyear --sim $sim" >> "$glost_task_file_ETCs"
    # fi
    # else
    #   echo "Output file $output_file_ETCs already exists. Skipping job submission for ${sim} ${iyear}."
    # fi
    if [ ! -f "$output_file_EETCs" ]; then
      echo "python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/ETCs_1000km.py $iyear --sim $sim --ext" >> "$glost_task_file_EETCs"
    else
      echo "Output file $output_file_EETCs already exists. Skipping job submission for ${sim} ${iyear}."
    fi
  done
done

# . /home/vdemeyer/TRACKING/KATJA/JOBS/generate_tasks_ETCs_1000km.sh