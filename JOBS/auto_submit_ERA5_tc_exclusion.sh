#!/bin/bash

# Waits for the end of the ERA5 geopotential download, then submits the first steps of the
# ERA5 chain (run_ERA5_tc_exclusion.sh labels: phase space and labels) if all 420 monthly
# files are present and the code is on the feature branch. The costly steps are submitted
# by hand once the labels have been checked. Run detached on a login node:
#   nohup setsid bash /home/vdemeyer/TRACKING/KATJA/JOBS/auto_submit_ERA5_tc_exclusion.sh > /home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/auto_submit_ERA5_tc_exclusion.log 2>&1 &

REPO=/home/vdemeyer/TRACKING/KATJA
ZG=/home/vdemeyer/projects/rrg-gachon/vdemeyer/ERA5/ZG
BRANCH=feature/tc-phase-classification

while pgrep -u "$USER" -f "^python download_ERA5_geopotential.py" > /dev/null; do
  sleep 600
done

n=$(ls $ZG/*/*/era5_z_ll_*_6h.nc4 2>/dev/null | wc -l)
echo "$(date): download finished, $n monthly files"
if [[ $n -lt 420 ]]; then
  echo "Missing files: chain NOT submitted. Rerun the download (it skips complete months)."
  exit 1
fi
if [[ "$(git -C $REPO branch --show-current)" != "$BRANCH" ]]; then
  echo "The repository is not on $BRANCH: chain NOT submitted."
  exit 1
fi
bash $REPO/JOBS/run_ERA5_tc_exclusion.sh labels
