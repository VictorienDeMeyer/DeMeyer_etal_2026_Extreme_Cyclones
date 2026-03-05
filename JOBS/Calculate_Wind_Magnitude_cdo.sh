#!/bin/bash

# Répertoires des fichiers u et v
dir_base="/home/vdemeyer/projects/rrg-gachon/vdemeyer"
dir_u="$dir_base/$1/UAS"
dir_v="$dir_base/$1/VAS"
output_dir="$dir_base/$1/WIND"

# Créer le répertoire de sortie s'il n'existe pas
mkdir -p "$output_dir"

# Fichier u et v à traiter
file_u="$2"
file_v="${file_u/$dir_u/$dir_v}"
file_v="${file_v/uas/vas}" #file_v="${file_v/u10/v10}" pour ERA5

# Nom du fichier de sortie avec la même arborescence
output_file="${file_u/$dir_u/$output_dir}"
output_file="${output_file/uas/wind10}" # output_file="${output_file/u10/wind10}"  pour ERA5

# Vérifier si le fichier v existe
if [ -f "$file_v" ]; then
    # Créer le répertoire de sortie s'il n'existe pas
    mkdir -p "$(dirname "$output_file")"

    # Calculer le module du vent et renommer la variable en surf_wind
    temp_file=$(mktemp)
    cdo -sqrt -add -sqr "$file_u" -sqr "$file_v" "$temp_file"
    cdo -setname,surf_wind "$temp_file" "$output_file"
    rm "$temp_file"

    # Ajouter les attributs à la variable surf_wind
    ncatted -O -a long_name,surf_wind,o,c,"Near-Surface Wind Magnitude" \
            -a units,surf_wind,o,c,"m/s" \
            -a description,surf_wind,o,c,"Near-Surface Wind Magnitude calculated from uas and vas components" \
            "$output_file"

    # Supprimer les autres variables
    ncks -O -v surf_wind "$output_file" "$output_file"

    # Compresser le fichier de sortie
    ncks -4 -L 4 -O "$output_file" "$output_file"

    echo "$output_file done"
else
    echo "!! No $file_v for $file_u"
fi