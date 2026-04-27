#!/bin/bash
#SBATCH --time=08:00:00
#SBATCH --account=rrg-gachon
#SBATCH --nodes=10
#SBATCH --ntasks-per-node=6               # 6 x 40G = 240G/node, fits on standard Narval nodes (~249G)
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=40G
#SBATCH --job-name=contrib_ETCs
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/OUTPUTS/contrib_ETCs_glost_output_%j.log

module load StdEnv/2023 gcc/12.3 openmpi/4.1.5 glost/0.3.1
module load python gcc arrow/14.0.1 scipy-stack/2024a ipykernel/2024a geos proj netcdf
source /home/vdemeyer/pytrack/bin/activate

glost_task_file="/home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/TASKS/glost_tasks_contribution_ETCs.txt"

if [[ ! -s "$glost_task_file" ]]; then
  echo "ERROR: $glost_task_file does not exist or is empty."
  echo "Run first: . /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/generate_tasks_glost_contribution_ETCs.sh"
  exit 1
fi

echo "Launching GLOST on $(wc -l < "$glost_task_file") tasks"

srun glost_launch "$glost_task_file"

# Workflow:
# 1. . /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/generate_tasks_glost_contribution_ETCs.sh
# 2. sbatch /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/submit_glost_job_contribution_ETCs.sh
# Check failures: grep "exit code" /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/OUTPUTS/contrib_ETCs_glost_output_<JOBID>.log | grep -v "exit code 0"
