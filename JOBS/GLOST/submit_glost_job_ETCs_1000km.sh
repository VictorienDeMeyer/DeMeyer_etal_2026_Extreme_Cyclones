#!/bin/bash
#SBATCH --time=06:00:00
#SBATCH --account=rrg-gachon
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=12              # 12 × 20G = 240G/nœud, tient sur nœuds standards Narval (~249G)
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=20G
#SBATCH --job-name=ETCs_1000km
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/OUTPUTS/ETCs_1000km_glost_output_%j.log

module load StdEnv/2023 gcc/12.3 openmpi/4.1.5 glost/0.3.1
module load python/3.11 mpi4py/4.0.3 esmf scipy-stack/2024a geos proj

glost_task_file="/home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/TASKS/glost_tasks_ETCs_1000km.txt"

if [[ ! -s "$glost_task_file" ]]; then
  echo "ERREUR : $glost_task_file n'existe pas ou est vide."
  echo "Lance d'abord : . /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/generate_tasks_glost_ETCs_1000km.sh"
  exit 1
fi

echo "Lancement GLOST sur $(wc -l < "$glost_task_file") tâches"

srun glost_launch "$glost_task_file"

# Workflow :
# 1. . /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/generate_tasks_glost_ETCs_1000km.sh
# 2. sbatch /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/submit_glost_job_ETCs_1000km.sh
# Vérifier les échecs : grep "exit code" /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/OUTPUTS/ETCs_1000km_glost_output_<JOBID>.log | grep -v "exit code 0"
