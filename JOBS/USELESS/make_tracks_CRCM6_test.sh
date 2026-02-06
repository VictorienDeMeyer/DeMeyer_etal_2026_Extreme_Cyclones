#!/bin/bash

module load gcc netcdf-fortran

TRACKS=/home/vdemeyer/TRACKING/KATJA/storm_tracks.Abs

# Construire le chemin des fichiers pour les années spécifiées
main_file="/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/INPUTS/${3}/${3}_psl_smoothed_400km_${1}-${2}_1month_pres.nc"
output_file="/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/${3}_psl_smoothed_400km_12h_990hPa_${1}-${2}_1month.txt"

$TRACKS -s ${main_file} -txt ${output_file} -nf_pres slp -p_field PN -c_field 'PN' -vcrit 0 -p_min 990 -minh 12 -quiet

#. /home/vdemeyer/TRACKING/KATJA/JOBS/make_tracks_CRCM6_test.sh 2000 2009 UBF