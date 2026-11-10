#!/bin/bash

# Orchestrator of the ERA5 test of the tropical cyclone exclusion. Submits, with
# dependencies (each step starts only if the previous one succeeded):
#   1. cyclone phase space parameters, ERA5 1980-2014       (submit_jobs_cyclone_phase_space.sh)
#   2. TC / TRANSITION / ETC labels + IBTrACS validation    (submit_classify_cyclone_phase.sh)
#   3. storm IDs within 1000 km without TCs                  (submit_jobs_ETCs_1000km.sh)
#   4. contribution to extreme precipitation and wind       (submit_jobs_contribution_ETCs.sh)
#   5. concatenation of the contributions                   (concat_contribution_ETCs_calc.sh)
#   6. cyclone track density without TCs                     (calculate_kde.sh)
#   7. figures                                              (plot_ERA5_TC_exclusion.sh)
# Requires the ERA5 geopotential on pressure levels in ERA5/ZG (see README).
# The array indices below select ERA5 in the task lists of the job scripts.
#
# Usage: bash /home/vdemeyer/TRACKING/KATJA/JOBS/run_ERA5_tc_exclusion.sh [all|labels|heavy]
#   all    : steps 1-7 (default)
#   labels : steps 1-2 only, to check the labels before the costly steps
#   heavy  : steps 3-7 only, once the labels have been checked

MODE=${1:-all}
if [[ "$MODE" != all && "$MODE" != labels && "$MODE" != heavy ]]; then
  echo "Unknown mode '$MODE' (all, labels or heavy)"
  exit 1
fi

J=/home/vdemeyer/TRACKING/KATJA/JOBS
OUT=$J/OUTPUTS
TC_FILTER=phase

after_labels=()
if [[ "$MODE" != heavy ]]; then
  j1=$(sbatch --parsable --array=0-34 $J/submit_jobs_cyclone_phase_space.sh)
  j2=$(sbatch --parsable --array=0 --dependency=afterok:$j1 $J/submit_classify_cyclone_phase.sh)
  echo "Submitted: CPS $j1 -> classify $j2"
  if [[ "$MODE" == labels ]]; then
    exit 0
  fi
  after_labels=(--dependency=afterok:$j2)
fi

j3=$(sbatch --parsable --array=0-34 "${after_labels[@]}" --export=ALL,TC_FILTER=$TC_FILTER $J/submit_jobs_ETCs_1000km.sh)
j4=$(sbatch --parsable --array=0-69 --dependency=afterok:$j3 --export=ALL,TC_FILTER=$TC_FILTER $J/submit_jobs_contribution_ETCs.sh)
j5=$(sbatch --parsable --array=0 --dependency=afterok:$j4 --export=sims_str=ERA5,TC_FILTER=$TC_FILTER \
            --job-name=concat_contrib_ERA5 $J/concat_contribution_ETCs_calc.sh)
j6=$(sbatch --parsable --array=0 "${after_labels[@]}" --export=sims_str=ERA5,season=ALL,TC_FILTER=$TC_FILTER \
            --job-name=ALL_calculate_kde_ERA5 --time=04:00:00 -o "$OUT/%x_%a.out" $J/calculate_kde.sh)
# pairs_str goes through the environment: --export would split it on its commas
j7=$(pairs_str="ERA5,DJF ERA5,MAM ERA5,JJA ERA5,SON" sbatch --parsable --array=0-3 "${after_labels[@]}" \
            --export=ALL,TC_FILTER=$TC_FILTER \
            --job-name=calculate_kde_ERA5 --time=01:00:00 -o "$OUT/%x_%a.out" $J/calculate_kde.sh)
j8=$(sbatch --parsable --dependency=afterok:$j5:$j6:$j7 $J/plot_ERA5_TC_exclusion.sh)

echo "Submitted: 1000km $j3 -> contribution $j4 -> concat $j5; density $j6 $j7; figures $j8"
