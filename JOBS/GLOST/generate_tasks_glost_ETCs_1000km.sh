#!/bin/bash

# Génère le fichier de tâches GLOST pour ETCs_1000km.
# À lancer AVANT le sbatch du glost job.

sims=("ERA5" "UBB" "UBD" "UBE" "UBF" "UBG" "UBH" "UBI")

glost_task_file="/home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/TASKS/glost_tasks_ETCs_1000km.txt"
mkdir -p "$(dirname "$glost_task_file")"
> "$glost_task_file"

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

  for iyear in $(seq $start_year $end_year); do
    echo "bash /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/ETCs_1000km.sh ${iyear} ${sim}" >> "$glost_task_file"
  done
done

echo "Tâches générées : $(wc -l < "$glost_task_file") dans $glost_task_file"

# . /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/generate_tasks_glost_ETCs_1000km.sh
