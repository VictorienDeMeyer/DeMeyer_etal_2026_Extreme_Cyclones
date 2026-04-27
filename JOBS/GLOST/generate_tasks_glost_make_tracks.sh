#!/bin/bash

# Génère le fichier de tâches GLOST pour make_tracks.
# À lancer AVANT le sbatch du glost job.

sims=("ERA5" "UBB" "UBD" "UBE" "UBF" "UBG" "UBH" "UBI")

glost_task_file="/home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/TASKS/glost_tasks_make_tracks.txt"
mkdir -p "$(dirname "$glost_task_file")"
> "$glost_task_file"

for sim in "${sims[@]}"; do
  if [[ "$sim" == "UBG" || "$sim" == "UBH" || "$sim" == "UBI" ]]; then
    start_year=2062
    end_year=2097
  else
    start_year=1979
    end_year=2014
  fi

  for iyear in $(seq $start_year $end_year); do
    echo "bash /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/make_tracks.sh ${iyear} ${sim}" >> "$glost_task_file"
  done
done

echo "Tâches générées : $(wc -l < "$glost_task_file") dans $glost_task_file"

# . /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/generate_tasks_glost_make_tracks.sh
