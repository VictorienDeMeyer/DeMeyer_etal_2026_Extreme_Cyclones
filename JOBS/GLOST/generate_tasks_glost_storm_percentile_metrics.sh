#!/bin/bash

# Génère le fichier de tâches GLOST pour storm_percentile_metrics.
# À lancer AVANT le sbatch du glost job.

sims=("UBD" "UBE" "UBF" "UBG" "UBH" "UBI")
quantiles=("99" "99.9")

glost_task_file="/home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/TASKS/glost_tasks_storm_percentile_metrics.txt"
mkdir -p "$(dirname "$glost_task_file")"
> "$glost_task_file"

for sim in "${sims[@]}"; do
  if [[ "$sim" == "UBG" || "$sim" == "UBH" || "$sim" == "UBI" ]]; then
    start_year=2063
    end_year=2097
  else
    start_year=1980
    end_year=2014
  fi

  for iyear in $(seq $start_year $end_year); do
    for quantile in "${quantiles[@]}"; do
      echo "bash /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/storm_percentile_metrics.sh ${iyear} ${sim} ${quantile}" >> "$glost_task_file"
    done
  done
done

echo "Tâches générées : $(wc -l < "$glost_task_file") dans $glost_task_file"

# . /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/generate_tasks_glost_storm_percentile_metrics.sh
