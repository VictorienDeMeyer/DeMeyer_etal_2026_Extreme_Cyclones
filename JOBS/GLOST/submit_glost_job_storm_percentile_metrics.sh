#!/bin/bash
#SBATCH --time=03:45:00
#SBATCH --account=rrg-gachon
#SBATCH --ntasks=20
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=700G
#SBATCH --job-name=storm_percentile_metrics
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/OUTPUTS/storm_percentile_metrics_glost_output_%j.log

module load StdEnv/2023 gcc/12.3 openmpi/4.1.5 glost/0.3.1
module load python/3.11 mpi4py/4.0.3 esmf scipy-stack/2024a geos proj

glost_task_file="/home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/TASKS/glost_tasks_storm_percentile_metrics.txt"

if [[ ! -s "$glost_task_file" ]]; then
  echo "ERREUR : $glost_task_file does not exist or is not valid."
  echo "First, run : . /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/generate_tasks_glost_storm_percentile_metrics.sh"
  exit 1
fi

echo "Lancement GLOST sur $(wc -l < "$glost_task_file") tâches"

srun glost_launch "$glost_task_file"

# Workflow :
# 1. . /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/generate_tasks_glost_storm_percentile_metrics.sh
# 2. sbatch /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/submit_glost_job_storm_percentile_metrics.sh
