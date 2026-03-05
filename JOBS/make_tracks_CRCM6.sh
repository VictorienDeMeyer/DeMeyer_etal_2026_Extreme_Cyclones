#!/bin/bash
#SBATCH --time=00:15:00
#SBATCH --account=rrg-gachon
#SBATCH --mem=70G
#SBATCH --ntasks=1

#Shell script to submit ESCER tracking algorithm as a job to the scheduler. It goes with the submit_jobs.sh script.

module load gcc netcdf-fortran

TRACKS=/home/vdemeyer/TRACKING/KATJA/storm_tracks.Abs

# Construire le chemin des fichiers pour les années spécifiées
main_file="/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/INPUTS/${2}/${2}_psl_smoothed_400km_${1}_1month_pres.nc"
output_file="/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/${2}_psl_smoothed_400km_12h_1005hPa_${1}_1month.txt"

if [ -f "$output_file" ]; then
    rm "$output_file"
fi

$TRACKS -s ${main_file} -txt ${output_file} -nf_pres slp -p_field PN -c_field 'PN' -vcrit 0 -p_min 1005 -minh 12 -mask /home/vdemeyer/projects/rrg-gachon/vdemeyer/MASK/mask_CRCM6_grid_for_CRCM6_eroded.nc -quiet

# sbatch --job-name=${sim}_psl_smooth_400km_12h_1005hPa_${year} -o "/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/${sim}_psl_smooth_400km_12h_1005hPa_${year}.out" /home/vdemeyer/TRACKING/KATJA/JOBS/make_tracks_CRCM6_new.sh 1979 UBB