import os
import argparse

import numpy as np
import pandas as pd

from ETC_tools import open_df, phase_file

"""
Label every time step of every tracked cyclone as tropical ('TC'), in transition
('TRANSITION') or extratropical ('ETC') from the cyclone phase space parameters
computed by cyclone_phase_space.py.

Steps, for each storm:
  1. 24-h running mean (centered) of B, -VTL and -VTU (Hart 2003), then linear
     interpolation in time to all the (hourly) track points. Points farther than
     MAX_GAP_H from a valid CPS value stay undefined.
  2. Tropical phase: deep, symmetric warm core, i.e. B < B_CRIT and -VTL > 0 and
     -VTU > 0, persisting for at least MIN_TC_HOURS equatorward of TC_MAX_LAT.
     Requiring a deep warm core (-VTU > 0) avoids labelling warm-seclusion
     extratropical cyclones, which only have a shallow warm core (-VTL > 0,
     -VTU < 0), as tropical (Hart 2003). The latitude limit removes the deep warm
     cores diagnosed in mature high-latitude cyclones (Labrador Sea, south of
     Greenland, Gulf of Alaska, mostly in winter): against IBTrACS (1980-2014), it
     reduces the false alarm ratio from 42% to 1% for ERA5 and from 50% to 2% for UBB,
     for one missed tropical storm out of about 100. A tropical cyclone that moves
     poleward of TC_MAX_LAT keeps its 'TC' label until the transition criteria below.
  3. Storms without a tropical phase: every time step is 'ETC'.
  4. Storms with a tropical phase (tropical cyclones and their extratropical
     transition, ET):
       - forward in time from the first tropical time step, ET onset is the first
         time the storm becomes asymmetric (B >= B_CRIT) or cold core (-VTL < 0),
         and ET completion the first time both criteria are met (Bieli et al. 2019;
         Garin et al. 2025). Time steps between onset and completion are
         'TRANSITION', time steps after completion are 'ETC'. A new tropical phase
         resets the storm to 'TC'.
       - backward in time from the first tropical time step, the same criteria
         identify a tropical transition of an extratropical precursor: time steps
         before the precursor is both asymmetric and cold core are 'ETC', the
         following ones 'TRANSITION' until the cyclone is again symmetric and
         warm core ('TC').
     Undefined CPS values never trigger a change of phase.

Output: {BASE}/{sim}/STORM_RELATED/TRACK/{sim}_psl_smooth_400km_24h_1000hPa_phase.txt
  Same columns as the connected track file, plus B, minus_VTL, minus_VTU (smoothed and
  interpolated), cps_valid, phase ('TC', 'TRANSITION', 'ETC') and tc_storm (True if the
  storm has a tropical phase at any time). Read it with ETC_tools.open_df(sim, tc_filter=...).

A summary of the classification is printed and saved next to the CPS files.

Author: Dr Victorien De Meyer
Year: 2026
"""

BASE = '/home/vdemeyer/projects/rrg-gachon/vdemeyer'

B_CRIT = 10.          # Thermal asymmetry threshold [m] (Hart 2003; Evans and Hart 2003)
SMOOTH_WINDOW_H = 24  # Running mean window of the CPS parameters [h] (Hart 2003)
MAX_GAP_H = 12        # Maximum distance [h] to a valid CPS value for interpolation
MIN_TC_HOURS = 24     # Minimum duration [h] of a deep symmetric warm core to be a tropical phase
TC_MAX_LAT = 40.      # Deep symmetric warm cores poleward of this latitude do not define a tropical phase [deg]

PHASES = ['TC', 'TRANSITION', 'ETC']


def years_of(sim):
    if sim in ['UBG', 'UBH', 'UBI']:
        return range(2063, 2098)
    return range(1980, 2015)


def load_cps(sim, years):
    files = [f'{BASE}/{sim}/STORM_RELATED/CPS/cps_{sim}_{year}.csv' for year in years]
    missing = [f for f in files if not os.path.exists(f)]
    if missing:
        raise FileNotFoundError(f'{len(missing)} missing CPS files, e.g. {missing[0]}')
    cps = pd.concat([pd.read_csv(f, parse_dates=['date']) for f in files], ignore_index=True)
    return cps.sort_values(['storm', 'date']).reset_index(drop=True)


def running_mean(t_hours, values, window_h=SMOOTH_WINDOW_H):
    """Centered running mean over +- window_h/2 in time, ignoring NaN."""
    out = np.full(values.shape, np.nan)
    for k, t0 in enumerate(t_hours):
        sel = (np.abs(t_hours - t0) <= window_h / 2.) & np.isfinite(values)
        if sel.any():
            out[k] = values[sel].mean()
    return out


def interpolate_to_track(t_cps, values, t_track, max_gap_h=MAX_GAP_H):
    """Linear interpolation of the valid CPS values to the track times, NaN beyond max_gap_h."""
    ok = np.isfinite(values)
    out = np.full(t_track.shape, np.nan)
    if not ok.any():
        return out
    t_ok, v_ok = t_cps[ok], values[ok]
    out[:] = np.interp(t_track, t_ok, v_ok)
    pos = np.searchsorted(t_ok, t_track)
    dist_prev = np.abs(t_track - t_ok[np.clip(pos - 1, 0, len(t_ok) - 1)])
    dist_next = np.abs(t_ok[np.clip(pos, 0, len(t_ok) - 1)] - t_track)
    out[np.minimum(dist_prev, dist_next) > max_gap_h] = np.nan
    return out


def tropical_runs(deep_warm_sym, t_hours, min_hours=MIN_TC_HOURS):
    """Keep only the runs of consecutive True values lasting at least min_hours."""
    is_tc = np.zeros_like(deep_warm_sym)
    k, n = 0, len(deep_warm_sym)
    # Duration counted with the time step, e.g. 24 hourly points = 24 h
    dt = np.median(np.diff(t_hours)) if n > 1 else 1.
    while k < n:
        if not deep_warm_sym[k]:
            k += 1
            continue
        end = k
        while end + 1 < n and deep_warm_sym[end + 1]:
            end += 1
        if t_hours[end] - t_hours[k] + dt >= min_hours:
            is_tc[k:end + 1] = True
        k = end + 1
    return is_tc


def label_storm(B, vtl, vtu, lat, t_hours, b_crit=B_CRIT, min_tc_hours=MIN_TC_HOURS, tc_max_lat=TC_MAX_LAT):
    """
    Phase of each time step of one storm.

    :return: (labels array of 'TC'/'TRANSITION'/'ETC', True if the storm has a tropical phase)
    """
    n = len(B)
    with np.errstate(invalid='ignore'):
        deep_warm_sym = (B < b_crit) & (vtl > 0) & (vtu > 0)   # False where undefined
        if tc_max_lat is not None:
            deep_warm_sym &= np.abs(lat) <= tc_max_lat
        asym = B >= b_crit
        cold = vtl < 0
    is_tc = tropical_runs(deep_warm_sym, t_hours, min_tc_hours)

    labels = np.full(n, 'ETC', dtype=object)
    if not is_tc.any():
        return labels, False

    first = int(np.argmax(is_tc))

    # Forward: tropical phase -> extratropical transition
    state = 'TC'
    for k in range(first, n):
        if is_tc[k]:
            state = 'TC'
        else:
            if state == 'TC' and (asym[k] or cold[k]):
                state = 'TRANSITION'
            if state == 'TRANSITION' and asym[k] and cold[k]:
                state = 'ETC'
        labels[k] = state

    # Backward: tropical phase <- tropical transition of an extratropical precursor
    state = 'TC'
    for k in range(first - 1, -1, -1):
        if state == 'TC' and (asym[k] or cold[k]):
            state = 'TRANSITION'
        if state == 'TRANSITION' and asym[k] and cold[k]:
            state = 'ETC'
        labels[k] = state

    return labels, True


def classify(track, cps):
    """Smooth, interpolate and label all storms. Returns the track DataFrame with new columns."""
    track = track.sort_values(['storm', 'date']).reset_index(drop=True)
    cps_groups = dict(tuple(cps.groupby('storm')))
    ref = np.datetime64('1970-01-01T00:00:00')

    cols = {c: np.full(len(track), np.nan) for c in ['B', 'minus_VTL', 'minus_VTU']}
    phase = np.full(len(track), 'ETC', dtype=object)
    tc_storm = np.zeros(len(track), dtype=bool)

    for storm, g in track.groupby('storm', sort=False):
        idx = g.index.values
        t_track = (g['date'].values - ref) / np.timedelta64(1, 'h')
        c = cps_groups.get(storm)
        if c is not None and len(c) > 0:
            t_cps = (c['date'].values - ref) / np.timedelta64(1, 'h')
            for name in cols:
                smoothed = running_mean(t_cps, c[name].values.astype(float))
                cols[name][idx] = interpolate_to_track(t_cps, smoothed, t_track)
        labels, is_tc_storm = label_storm(cols['B'][idx], cols['minus_VTL'][idx], cols['minus_VTU'][idx],
                                          g['lat'].values, t_track)
        phase[idx] = labels
        tc_storm[idx] = is_tc_storm

    for name, values in cols.items():
        track[name] = values
    track['cps_valid'] = np.isfinite(track['B']) & np.isfinite(track['minus_VTL']) & np.isfinite(track['minus_VTU'])
    track['phase'] = phase
    track['tc_storm'] = tc_storm
    return track


def summary(track, sim):
    """Print and return a summary of the classification."""
    storms = track.groupby('storm').agg(tc_storm=('tc_storm', 'first'),
                                        start=('date', 'min'),
                                        lat_start=('lat', 'first'))
    lines = [
        f'Classification summary for {sim}',
        f'  storms                          : {len(storms)}',
        f'  storms with a tropical phase    : {storms["tc_storm"].sum()} ({storms["tc_storm"].mean()*100:.1f}%)',
        f'  track points with valid CPS     : {track["cps_valid"].mean()*100:.1f}%',
    ]
    for p in PHASES:
        lines.append(f'  track points labelled {p:<10}: {(track["phase"] == p).mean()*100:.2f}%')
    tc = storms[storms['tc_storm']]
    if len(tc) > 0:
        months = tc['start'].dt.month.value_counts().sort_index()
        lines.append('  storms with a tropical phase per starting month: '
                     + ', '.join(f'{m}:{n}' for m, n in months.items()))
        tc_points = track[track['phase'] == 'TC']
        lines.append(f'  latitude of TC points (5/50/95th percentiles): '
                     f'{np.percentile(tc_points["lat"], [5, 50, 95]).round(1).tolist()}')
    text = '\n'.join(lines)
    print(text)
    return text


def main(sim):
    track_raw = open_df(sim, period_filtering=False)
    cps = load_cps(sim, years_of(sim))
    print(f'{sim}: {len(track_raw)} track points, {len(cps)} CPS points')

    track = classify(track_raw, cps)

    output_file = phase_file(sim)
    track.to_csv(output_file, sep=' ', index=False, float_format='%.4f', date_format='%Y-%m-%d %H:%M:%S')
    print(f'Saved {output_file}\n')

    text = summary(track, sim)
    with open(f'{BASE}/{sim}/STORM_RELATED/CPS/classification_summary_{sim}.txt', 'w') as f:
        f.write(text + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Label tracked cyclones as TC / TRANSITION / ETC at each time step')
    parser.add_argument('--sim', type=str, required=True, help='Name of the simulation')
    args = parser.parse_args()
    main(args.sim)

# run /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/classify_cyclone_phase.py --sim ERA5
