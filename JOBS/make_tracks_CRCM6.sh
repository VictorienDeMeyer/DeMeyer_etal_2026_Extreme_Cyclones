#!/bin/bash
#SBATCH --time=01:00:00
#SBATCH --account=rrg-gachon
#SBATCH --mem=200G
#SBATCH --ntasks=1

#Shell script to submit ESCER tracking algorithm as a job to the scheduler. It goes with the submit_jobs.sh script.

module load gcc netcdf-fortran

TRACKS=/home/vdemeyer/TRACKING/KATJA/storm_tracks.Abs

# Construire le chemin des fichiers pour les années spécifiées
main_file="/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/INPUTS/${3}/${3}_psl_smoothed_400km_${1}-${2}_1month_pres.nc"
output_file="/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/${3}_psl_smoothed_400km_12h_1005hPa_${1}-${2}_1month.txt"

if [ -f "$output_file" ]; then
    rm "$output_file"
fi

$TRACKS -s ${main_file} -txt ${output_file} -nf_pres slp -p_field PN -c_field 'PN' -vcrit 0 -p_min 1005 -minh 12 -mask /home/vdemeyer/projects/rrg-gachon/vdemeyer/MASK/mask_CRCM6_grid_for_CRCM6_eroded.nc -quiet

#sbatch /home/vdemeyer/TRACKING/KATJA/JOBS/make_tracks_CRCM6.sh 2010 2014 UBF