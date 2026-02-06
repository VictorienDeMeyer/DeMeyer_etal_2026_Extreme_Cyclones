#!/bin/bash
#SBATCH --time=06:00:00
#SBATCH --account=rrg-gachon
#SBATCH --nodes=3                        # Nombre de nœuds (26 * 60 = 1560 tâches)
#SBATCH --ntasks-per-node=15              # 60 tâches par nœud
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=25G
#SBATCH --job-name=EETCs_stat
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/EETCs_stat_glost_output_%j.log

module load StdEnv/2023 gcc/12.3 openmpi/4.1.5 glost/0.3.1
module load python gcc arrow/14.0.1 scipy-stack/2024a ipykernel/2024a geos proj netcdf
source /home/vdemeyer/pytrack/bin/activate

srun glost_launch /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/glost_tasks_EETCs_stat.txt

# sbatch /home/vdemeyer/TRACKING/KATJA/JOBS/submit_glost_job_EETCs_stat.sh