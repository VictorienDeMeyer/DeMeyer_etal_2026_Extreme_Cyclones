#!/bin/bash
#SBATCH --time=30:00:00
#SBATCH --account=rrg-gachon
#SBATCH --nodes=2                         # Nombre de nœuds (26 * 60 = 1560 tâches)
#SBATCH --ntasks-per-node=8              # 60 tâches par nœud
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=50G
#SBATCH --job-name=contrib_ETCs
#SBATCH --output=/home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/contrib_ETCs_glost_output_%j.log

module load StdEnv/2023 gcc/12.3 openmpi/4.1.5 glost/0.3.1
module load python gcc arrow/14.0.1 scipy-stack/2024a ipykernel/2024a geos proj netcdf
source /home/vdemeyer/pytrack/bin/activate

srun glost_launch /home/vdemeyer/TRACKING/KATJA/JOBS/GLOST/glost_tasks_contribution_ETCs.txt

# sbatch /home/vdemeyer/TRACKING/KATJA/JOBS/submit_glost_job_contribution_ETCs.sh