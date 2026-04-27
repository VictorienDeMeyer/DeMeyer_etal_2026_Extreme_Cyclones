#!/bin/bash

# Generates the GLOST task file for contribution_ETCs.
# Run this BEFORE sbatch'ing the glost job.

sims=("ERA5" "UBB" "UBD" "UBE" "UBF" "UBG" "UBH" "UBI")
vars=("pr" "ws")

glost_task_file="/home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/TASKS/glost_tasks_contribution_ETCs.txt"
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

  for var in "${vars[@]}"; do
    for iyear in $(seq $start_year $end_year); do
      echo "bash /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/contribution_ETCs.sh ${iyear} ${sim} ${var}" >> "$glost_task_file"
    done
  done
done

echo "Generated $(wc -l < "$glost_task_file") tasks in $glost_task_file"

# . /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/generate_tasks_glost_contribution_ETCs.sh
