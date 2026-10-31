#!/bin/bash

# Orchestrator of the tropical cyclone exclusion for the CRCM6 simulations (UBB, UBD, UBE,
# UBF: 1980-2014; UBG, UBH, UBI: 2063-2097). Run it after the ERA5 chain
# (run_ERA5_tc_exclusion.sh), whose outputs are needed by the merge of the contributions.
# Submits, with dependencies (each step starts only if the previous one succeeded):
#   1. cyclone phase space parameters                       (submit_jobs_cyclone_phase_space.sh)
#   2. TC / TRANSITION / ETC labels (+ IBTrACS validation of UBB)  (submit_classify_cyclone_phase.sh)
#   3. storm IDs within 1000 km without TCs                  (submit_jobs_ETCs_1000km.sh)
#   4. contribution to extreme precipitation and wind       (submit_jobs_contribution_ETCs.sh)
#   5. storm exceedance metrics, land mask, NNA2 box        (submit_jobs_storm_percentile_metrics.sh)
#   6. concatenation of the contributions + merge of the 8 simulations (concat_contribution_ETCs_*.sh)
#   7. cyclone track density without TCs, ALL and per season (calculate_kde.sh)
# The array indices below select the CRCM6 simulations in the task lists of the job scripts.
# Test the phase space on two tasks first (UBB 1980 and UBH 2063) and check their time and
# memory with seff:
#   sbatch --array=35,210 --mem=24G /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_cyclone_phase_space.sh
#
# Usage: bash /home/vdemeyer/TRACKING/KATJA/JOBS/run_CRCM6_tc_exclusion.sh [all|labels|heavy]
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
BASE=/home/vdemeyer/projects/rrg-gachon/vdemeyer
TC_FILTER=phase
SIMS="UBB UBD UBE UBF UBG UBH UBI"

after_labels=()
if [[ "$MODE" != heavy ]]; then
  # All the monthly geopotential files must be there
  for sim in $SIMS; do
    n=$(ls $BASE/$sim/ZG/zg_${sim,,}_??????_se.nc 2>/dev/null | wc -l)
    if [[ $n -ne 420 ]]; then
      echo "$sim: $n geopotential files instead of 420. Nothing submitted."
      exit 1
    fi
  done

  # The CRCM6 months need about 20 GB (whole month read at once) and 7 min
  j1=$(sbatch --parsable --array=35-279%100 --mem=24G --time=00:30:00 $J/submit_jobs_cyclone_phase_space.sh)
  j2=$(sbatch --parsable --array=1-7 --dependency=afterok:$j1 $J/submit_classify_cyclone_phase.sh)
  echo "Submitted: CPS $j1 -> classify $j2"
  if [[ "$MODE" == labels ]]; then
    exit 0
  fi
  after_labels=(--dependency=afterok:$j2)
fi

j3=$(sbatch --parsable --array=35-279%100 "${after_labels[@]}" --export=ALL,TC_FILTER=$TC_FILTER $J/submit_jobs_ETCs_1000km.sh)
j4=$(sbatch --parsable --array=70-559%100 --dependency=afterok:$j3 --export=ALL,TC_FILTER=$TC_FILTER $J/submit_jobs_contribution_ETCs.sh)
j5=$(sbatch --parsable --dependency=afterok:$j3 --export=ALL,MASK=land,REGION=NNA2,TC_FILTER=$TC_FILTER \
            $J/submit_jobs_storm_percentile_metrics.sh)
j6=$(sbatch --parsable --array=0-6 --dependency=afterok:$j4 --export=sims_str="$SIMS",TC_FILTER=$TC_FILTER \
            --job-name=concat_contrib $J/concat_contribution_ETCs_calc.sh)
j7=$(sbatch --parsable --dependency=afterok:$j6 --export=TC_FILTER=$TC_FILTER \
            --job-name=All_concat_contrib $J/concat_contribution_ETCs_merge.sh)

pairs=()
for sim in $SIMS; do
  for season in DJF MAM JJA SON; do
    pairs+=("${sim},${season}")
  done
done
j8=$(sbatch --parsable --array=0-6 "${after_labels[@]}" --export=sims_str="$SIMS",season=ALL,TC_FILTER=$TC_FILTER \
            --job-name=ALL_calculate_kde --time=04:00:00 -o "$OUT/%x_%a.out" $J/calculate_kde.sh)
j9=$(sbatch --parsable --array=0-$((${#pairs[@]}-1)) "${after_labels[@]}" \
            --export=pairs_str="${pairs[*]}",TC_FILTER=$TC_FILTER \
            --job-name=calculate_kde --time=01:00:00 -o "$OUT/%x_%a.out" $J/calculate_kde.sh)

echo "Submitted: 1000km $j3 -> contribution $j4 -> concat $j6 -> merge $j7; storm metrics $j5; density $j8 $j9"
