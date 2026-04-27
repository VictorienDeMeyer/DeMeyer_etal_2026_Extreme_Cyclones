#!/bin/bash
#SBATCH --time=01:00:00
#SBATCH --account=rrg-gachon
#SBATCH --nodes=8                         # 8 nœuds en parallèle
#SBATCH --ntasks-per-node=2               # 2 tâches/nœud (validé : pas d'OOM avec ~124G effectifs/tâche)
#SBATCH --cpus-per-task=32                # demi-nœud par tâche (lié à la RAM, le binaire est mono-thread)
#SBATCH --mem=0                           # toute la mémoire du nœud (~249G), répartie entre les 2 tâches
#SBATCH --job-name=make_tracks
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/OUTPUTS/make_tracks_glost_output_%j.log

# Paramètres calibrés d'après le run 59562051 (COMPLETED en 40:55) :
# - ~288 tâches, 2 tâches/nœud × 8 nœuds → ~41 min réels. --time=1h = marge ×1.5.
# - Mémoire : --mem=0 avec 2 tâches/nœud est validé en pratique (pas d'OOM).
# - CPU : le binaire est mono-thread ; on réserve 32 cores/tâche uniquement
#   pour obtenir la RAM associée (~3.9G/core sur Narval). Sous-utilisation CPU
#   assumée et inévitable dans cette config memory-bound.
# - Si OOM un jour : repasser à --ntasks-per-node=1 / --cpus-per-task=64.

module load StdEnv/2023 gcc/12.3 openmpi/4.1.5 glost/0.3.1
module load gcc netcdf-fortran

glost_task_file="/home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/TASKS/glost_tasks_make_tracks.txt"

if [[ ! -s "$glost_task_file" ]]; then
  echo "ERREUR : $glost_task_file n'existe pas ou est vide."
  echo "Lance d'abord : . /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/generate_tasks_glost_make_tracks.sh"
  exit 1
fi

echo "Lancement GLOST sur $(wc -l < "$glost_task_file") tâches"

srun glost_launch "$glost_task_file"

# Workflow :
# 1. . /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/generate_tasks_glost_make_tracks.sh
# 2. sbatch /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/submit_glost_job_make_tracks.sh
