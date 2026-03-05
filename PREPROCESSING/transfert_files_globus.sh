#!/bin/bash

# ==============================
# Script to transfer files from UQAM servers to Narval using Globus. Here configurated for the 3 futures simulations only.
# ==============================

# ==============================
# Configuration
# ==============================
USER="vdemeyer"

ARRIME_ENDPOINT="5d31011b-75ac-459d-8956-a73c7941efc3"
SIERRAS_ENDPOINT="bd856a55-1adf-4fd3-85d7-46c159323f86"
DEST_ENDPOINT="a1713da6-098f-40e6-b3aa-034efe8b6e5b"

VARIABLES=("psl" "uas" "vas" "pr")
ARRIME_SIMS=("ubh" "ubi")
SIERRAS_SIMS=("ubg")

ARRIME_BATCH="/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/batch_ARRIME.txt"
SIERRAS_BATCH="/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/batch_sierra.txt"

> "$ARRIME_BATCH"
> "$SIERRAS_BATCH"

COUNT_ARRIME=0
COUNT_SIERRAS=0

echo "Génération des listes de transfert..."

# ==============================
# Function to generate batch files
# ==============================
generate_batch() {
    SIM_LIST=("${!1}")
    BATCH_FILE=$2
    COUNTER_NAME=$3

    for FILE_TYPE in "${SIM_LIST[@]}"; do
        for YEAR in {2083..2100}; do
            for MONTH in {01..12}; do

                YYYYMM="${YEAR}${MONTH}"

                for VAR_TYPE in "${VARIABLES[@]}"; do
                    FILE_NAME="${VAR_TYPE}_${FILE_TYPE}_${YYYYMM}_se.nc"
                    ENDPOINT_SOURCE_PATH="/arrime/NetCDF/ssp370/${FILE_TYPE}/${YYYYMM}/series/${FILE_NAME}"
                    DEST_DIR="/home/$USER/projects/rrg-gachon/$USER/${FILE_TYPE^^}/${VAR_TYPE^^}/"
                    DEST_PATH="${DEST_DIR}${FILE_NAME}"

                    echo "$ENDPOINT_SOURCE_PATH $DEST_PATH" >> "$BATCH_FILE"
                    eval "$COUNTER_NAME=\$(( $COUNTER_NAME + 1 ))"
                done
            done
        done
    done
}

# ==============================
# Natches generation
# ==============================
generate_batch ARRIME_SIMS[@] "$ARRIME_BATCH" COUNT_ARRIME
generate_batch SIERRAS_SIMS[@] "$SIERRAS_BATCH" COUNT_SIERRAS

echo "Fichiers ARRIME à transférer : $COUNT_ARRIME"
echo "Fichiers SIERRAS à transférer : $COUNT_SIERRAS"

# ==============================
# Submitting Transfer Jobs
# ==============================
if [ $COUNT_ARRIME -gt 0 ]; then
    globus transfer "$ARRIME_ENDPOINT" "$DEST_ENDPOINT" \
        --batch "$ARRIME_BATCH" \
        --label "ARRIME_ssp370_overwrite" \
        --sync-level checksum
fi

if [ $COUNT_SIERRAS -gt 0 ]; then
    globus transfer "$SIERRAS_ENDPOINT" "$DEST_ENDPOINT" \
        --batch "$SIERRAS_BATCH" \
        --label "SIERRAS_ssp370_overwrite" \
        --sync-level checksum
fi

echo "Transfert lancé. Vérifiez la progression avec : globus task list"