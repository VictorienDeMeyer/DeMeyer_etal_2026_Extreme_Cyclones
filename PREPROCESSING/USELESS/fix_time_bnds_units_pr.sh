#!/bin/bash

# Script to fix the units of the time_bnds variable in CRCM6 precipitation (pr) files.
# Some CRCM6 pr files have an inconsistency between the time and time_bnds variable
# units, which causes issues when opening files with xarray (e.g., sub-hourly precision,
# wrong calendar offsets). CDO's setreftime corrects both time and time_bnds to use
# the same reference date and unit.
#
# Usage: ./fix_time_bnds_units_pr.sh <sim_name> [base_dir]
# Example: ./fix_time_bnds_units_pr.sh UBB
# Example: ./fix_time_bnds_units_pr.sh UBB /custom/data/path

sim=$1
base_dir="${2:-${BASE_DIR:-/home/vdemeyer/projects/rrg-gachon/vdemeyer}}"

if [ -z "$sim" ]; then
    echo "Usage: $0 <sim_name> [base_dir]"
    echo "Example: $0 UBB"
    exit 1
fi

pr_dir="$base_dir/$sim/PR"

if [ ! -d "$pr_dir" ]; then
    echo "Error: Directory $pr_dir does not exist"
    exit 1
fi

echo "Fixing time_bnds units for $sim precipitation files in $pr_dir"

count=0
errors=0

for file in "$pr_dir"/pr_*.nc; do
    if [ ! -f "$file" ]; then
        echo "No precipitation files found in $pr_dir"
        exit 1
    fi

    tmp_file="$(mktemp -p "$pr_dir" --suffix=.nc)"

    # Fix time and time_bnds units using CDO:
    # setreftime sets the reference time and unit so that time_bnds units match time units.
    if cdo -s setreftime,1979-01-01,00:00:00,hours "$file" "$tmp_file"; then
        mv "$tmp_file" "$file"
        echo "Fixed: $(basename "$file")"
        ((count++))
    else
        echo "Error fixing: $(basename "$file")"
        rm -f "$tmp_file"
        ((errors++))
    fi
done

echo ""
echo "Done: $count files fixed, $errors errors"
