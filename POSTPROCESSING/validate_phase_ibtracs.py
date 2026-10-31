import os
import argparse
from glob import glob

import numpy as np
import pandas as pd

from ETC_tools import open_df
from cyclone_phase_space import haversine

"""
Evaluation of the TC / TRANSITION / ETC labels (classify_cyclone_phase.py) against the
IBTrACS best tracks, for ERA5 and for UBB (CRCM6 driven by ERA5 with spectral nudging,
so its cyclones are the observed ones).

Each IBTrACS point (North Atlantic and eastern North Pacific, synoptic hours) is matched
to the closest tracked cyclone center at the same time within MATCH_DIST_KM. A tracked
storm and an IBTrACS storm are paired when at least MIN_MATCHED_STEPS points match.

Outputs, printed and saved in {BASE}/{sim}/STORM_RELATED/CPS/:
  - validation_ibtracs_points_{sim}.csv : contingency table of the IBTrACS nature
      (TS: tropical, ET: extratropical, SS: subtropical, DS: disturbance, MX: mixed,
      NR: not reported) against our phase label, for all matched points.
  - validation_ibtracs_storms_{sim}.csv : one line per tracked storm with a tropical
      phase or paired with an IBTrACS storm, with the pairing result. Tracked storms
      with a tropical phase but no IBTrACS counterpart are candidate false alarms to
      inspect; IBTrACS tropical storms whose tracked counterpart has no tropical phase
      are misses.

IBTrACS files (download them once, e.g. on a login node, into IBTRACS_DIR):
  https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.NA.list.v04r01.csv
  https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.EP.list.v04r01.csv

Author: Dr Victorien De Meyer
Year: 2026
"""

BASE = '/home/vdemeyer/projects/rrg-gachon/vdemeyer'
IBTRACS_DIR = f'{BASE}/ALL/IBTRACS'

MATCH_DIST_KM = 300.
MIN_MATCHED_STEPS = 4      # 6-hourly synoptic times, i.e. 24 h
NATURES = ['TS', 'SS', 'ET', 'DS', 'MX', 'NR']
PHASES = ['TC', 'TRANSITION', 'ETC']


def load_ibtracs(years):
    files = sorted(glob(f'{IBTRACS_DIR}/ibtracs.*.list.v04r01.csv'))
    if not files:
        raise FileNotFoundError(f'No IBTrACS csv file in {IBTRACS_DIR}')
    ib = pd.concat([
        pd.read_csv(f, skiprows=[1], usecols=['SID', 'NAME', 'ISO_TIME', 'NATURE', 'LAT', 'LON'],
                    keep_default_na=False, na_values=['', ' '], low_memory=False)
        for f in files], ignore_index=True)
    ib['date'] = pd.to_datetime(ib['ISO_TIME'])
    ib = ib[(ib['date'].dt.minute == 0) & ib['date'].dt.hour.isin([0, 6, 12, 18])]
    ib = ib[ib['date'].dt.year.isin(list(years))]
    ib['LON'] = ((ib['LON'] + 180.) % 360.) - 180.
    return ib.drop_duplicates(['SID', 'date']).reset_index(drop=True)


def match_points(track, ib):
    m = ib.merge(track[['storm', 'date', 'lat', 'lon', 'phase', 'tc_storm']], on='date')
    m['dist'] = haversine(m['LON'].values, m['LAT'].values, m['lon'].values, m['lat'].values)
    m = m[m['dist'] <= MATCH_DIST_KM].sort_values('dist')
    # Closest tracked center for each IBTrACS point, and one IBTrACS point per tracked center
    m = m.drop_duplicates(['SID', 'date']).drop_duplicates(['storm', 'date'])
    counts = m.groupby(['SID', 'storm']).size()
    pairs = counts[counts >= MIN_MATCHED_STEPS].index
    return m.set_index(['SID', 'storm']).loc[pairs].reset_index()


def main(sim):
    years = range(1980, 2015)
    track = open_df(sim, period_filtering=True, tc_filter='phase', flag_only=True)
    ib = load_ibtracs(years)
    print(f'{sim}: {track["storm"].nunique()} tracked storms, {ib["SID"].nunique()} IBTrACS storms (NA + EP)')

    m = match_points(track, ib)
    print(f'{m["SID"].nunique()} IBTrACS storms paired with {m["storm"].nunique()} tracked storms '
          f'({len(m)} matched points)\n')

    # Point-level contingency table
    table = pd.crosstab(m['NATURE'], m['phase']).reindex(index=NATURES, columns=PHASES, fill_value=0)
    pct = table.div(table.sum(axis=1).replace(0, np.nan), axis=0) * 100
    print('Matched points: IBTrACS nature (rows) vs phase label (columns), counts')
    print(table)
    print('\nSame, in % of each row')
    print(pct.round(1))
    # With tc_filter='phase', the TC and TRANSITION time steps are removed and the ETC ones kept
    excluded_ts = table.loc['TS', ['TC', 'TRANSITION']].sum() / max(table.loc['TS'].sum(), 1) * 100
    kept_et = table.loc['ET', 'ETC'] / max(table.loc['ET'].sum(), 1) * 100
    print(f'\nIBTrACS tropical (TS) points excluded by the phase filter (TC + TRANSITION): {excluded_ts:.1f}%')
    print(f'IBTrACS extratropical (ET) points kept by the phase filter (ETC)           : {kept_et:.1f}%')

    # Storm-level evaluation
    ts_sids = set(m.loc[m['NATURE'] == 'TS', 'SID'])
    storms = track.groupby('storm').agg(start=('date', 'min'), end=('date', 'max'), tc_storm=('tc_storm', 'first'),
                                        n_tc_points=('phase', lambda x: (x == 'TC').sum()))
    paired = m.groupby('storm').agg(sid=('SID', lambda x: ','.join(sorted(set(x)))),
                                    name=('NAME', lambda x: ','.join(sorted(set(x.astype(str))))),
                                    ibtracs_tropical=('SID', lambda x: bool(set(x) & ts_sids)))
    storms = storms.join(paired, how='left')
    storms['paired'] = storms['sid'].notna()
    storms['ibtracs_tropical'] = storms['ibtracs_tropical'].fillna(False).astype(bool)
    storms = storms[storms['tc_storm'] | storms['paired']]

    hits = (storms['tc_storm'] & storms['ibtracs_tropical']).sum()
    misses = (~storms['tc_storm'] & storms['ibtracs_tropical']).sum()
    false_alarms = (storms['tc_storm'] & ~storms['ibtracs_tropical']).sum()
    print(f'\nTracked storms paired with an IBTrACS tropical storm : {hits + misses}')
    print(f'  with a tropical phase (hits)                        : {hits}'
          f' (POD = {hits / max(hits + misses, 1) * 100:.1f}%)')
    print(f'  without a tropical phase (misses)                   : {misses}')
    print(f'Tracked storms with a tropical phase                  : {storms["tc_storm"].sum()}')
    print(f'  not paired with an IBTrACS tropical storm           : {false_alarms}'
          f' (FAR = {false_alarms / max(hits + false_alarms, 1) * 100:.1f}%)')

    output_dir = f'{BASE}/{sim}/STORM_RELATED/CPS'
    os.makedirs(output_dir, exist_ok=True)
    table.to_csv(f'{output_dir}/validation_ibtracs_points_{sim}.csv')
    storms.to_csv(f'{output_dir}/validation_ibtracs_storms_{sim}.csv')
    print(f'\nSaved validation tables in {output_dir}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate the cyclone phase labels against IBTrACS')
    parser.add_argument('--sim', type=str, default='ERA5', choices=['ERA5', 'UBB'],
                        help='ERA5 or UBB (CRCM6 driven by ERA5 with spectral nudging)')
    args = parser.parse_args()
    main(args.sim)

# run /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/validate_phase_ibtracs.py --sim ERA5
