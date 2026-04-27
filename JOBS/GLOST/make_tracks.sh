#!/bin/bash

# Wrapper unifié ERA5/CRCM6 lancé par une tâche GLOST.
# Usage: bash make_tracks.sh <year> <sim>
# (pas de directives SBATCH ici : c'est GLOST qui gère les ressources)

year=$1
sim=$2

TRACKS=/home/vdemeyer/TRACKING/KATJA/storm_tracks.Abs

# Choix du masque selon la source
if [ "$sim" == "ERA5" ]; then
    mask="/home/vdemeyer/projects/rrg-gachon/vdemeyer/ALL/MASK/mask_CRCM6_grid_for_ERA5_0_360_eroded.nc"
else
    mask="/home/vdemeyer/projects/rrg-gachon/vdemeyer/ALL/MASK/mask_CRCM6_grid_for_CRCM6_eroded.nc"
fi

main_file="/home/vdemeyer/projects/rrg-gachon/vdemeyer/${sim}/PSL/SMOOTHED/${sim}_psl_smoothed_400km_${year}_pres.nc"
output_file="/home/vdemeyer/projects/rrg-gachon/vdemeyer/${sim}/STORM_RELATED/TRACK/${sim}_psl_smoothed_400km_12h_1000hPa_${year}_1month.txt"

if [ -f "$output_file" ]; then
    rm "$output_file"
fi

$TRACKS -s ${main_file} -txt ${output_file} -nf_pres slp -p_field PN -c_field 'PN' -vcrit 0 -p_min 1000 -minh 24 -span 1000 -mask ${mask} -quiet
