import calendar
import xarray as xr
import pandas as pd
import numpy as np
from glob import glob
from braceexpand import braceexpand
import os
import argparse
import gc

"""
This script computes per-storm exceedance metrics above the 99th percentile
for precipitation and wind, for a single year (iyear).

For each storm present in the year, it computes:
  - cum_excess_pr / cum_excess_wind: cumulative exceedance above the percentile
      (sum over masked grid-point-hours where pr/wind > percentile within 1000km of the storm)
  - count_exceed_pr / count_exceed_wind: number of masked grid-point-hours exceeding the threshold

Storms crossing year boundaries (e.g. Dec 30 to Jan 12) will appear in BOTH years' outputs
with partial cum/count values that can be summed in post-processing.
Storms are attributed to grid points via the closest-storm assignment.

The spatial mask is selectable via --mask:
  - land  : CRCM6 land-sea mask (sftlf > 0) -- any cell with > 0% land.
  - urban : DEGURBA-based populated-land mask -- any cell where
            frac_L1_urban_cluster + frac_L1_urban_centre > 0
            (i.e. any non-zero urban cluster or urban centre presence,
             corresponds to DEGURBA Level-2 classes >= 21 combined).
            The SAME E2025 SMOD mask is used for all simulations (both
            historical and future) so that occurrence / cumul metrics are
            not inflated in the future merely by urban expansion. The
            E2025 mask is produced by degurba_regrid_to_crcm6.py
            --epoch E2025.

In addition, regardless of --mask choice, cells south of LAT_MIN_NORTH
(default 30 N, geographic latitude) are discarded to avoid over-representing
tropical / subtropical cyclones in the extratropical-storm statistics.

Author: Dr Victorien De Meyer
Year: 2026
"""

# Minimum geographic latitude (deg N) kept by the spatial mask. Cells south of
# this are discarded regardless of the land/urban choice, to avoid tropical /
# subtropical cyclones contaminating the extratropical-storm statistics.
LAT_MIN_NORTH = 30.0

# CRCM6 reference file providing the 2D geographic latitude `lat(rlat, rlon)`.
# Any CRCM6 sim works since they all share the same rotated-pole grid.
CRCM6_REF_NC = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/UBD/PR/pr_ubd_197909_se.nc'


def braced_glob(path):
    l = []
    for x in braceexpand(path):
        l.extend(glob(x))          
    return l

def selection_percentile(sim, future_hist_sim, variable, wetdays=True, future=False):
    """
    Return an xarray Dataset for the requested percentile file.
    Copied from EETCs_stat.py (without original_selection).
    """
    base_dir = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/'
    settings = {
        'pr': {'dir': 'PR_Percentile', 'prefix': 'pr'},
        'ws': {'dir': 'WIND_Percentile', 'prefix': 'surf_wind'}
    }
    var_dir, prefix = settings[variable]['dir'], settings[variable]['prefix']

    base_sim = sim if future else future_hist_sim.get(sim, sim)
    wetdays_str = '_wetdays' if (wetdays and variable == 'pr') else ''
    period = (
        '2063-2097' if future and sim in future_hist_sim
        else '1980-2014'
    )
    filename = f"{prefix}_{base_sim.lower()}_percentile_{period}{wetdays_str}.nc"

    file_path = f"{base_dir}{base_sim}/{var_dir}/{filename}"
    print(f"\nLoading percentile file: {file_path}\n")

    percentile = xr.open_dataset(file_path)
    return percentile

def load_spatial_mask(mask_kind, sim, future_hist_sim, base):
    """
    Load the 2D boolean mask (rlat, rlon) to apply before counting exceedances.

    Parameters
    ----------
    mask_kind : {'land', 'urban'}
        'land'  -> CRCM6 land-sea mask: True where sftlf > 0 (any land fraction).
        'urban' -> DEGURBA-based populated-land mask: True where
                   frac_L1_urban_cluster + frac_L1_urban_centre > 0.
                   Picks E2025 for both historical and future sims.
    sim, future_hist_sim, base : as in main().

    Returns
    -------
    mask : np.ndarray of bool, shape (rlat, rlon)
    mask_tag : str
        Short tag used in the output filename to make the mask choice traceable
        (e.g. 'landonly', 'urbanonly_DEGURBAE1995').
    """
    if mask_kind == 'land':
        ds_lsm = xr.open_dataset(f'{base}/ALL/MASK/CRCM6_lsmsk.nc4')
        mask = (ds_lsm.sftlf.squeeze() > 0).values
        tag = 'landonly'
    elif mask_kind == 'urban':
        # Single, fixed E2025 urban mask for BOTH historical and future sims.
        # Rationale: using different masks for hist (E1995) and fut (E2085) would
        # inflate occurrence and cumul in the future just because the future
        # urban footprint has more grid points. Holding the mask fixed isolates
        # the climate-driven change from the urban-expansion signal.
        mask_path = f'{base}/ALL/MASK/GHS_SMOD_E2025_GLOBE_R2023A_54009_1000_V2_0_CRCM6grid.nc'
        print(f"Loading DEGURBA urban mask (E2025, fixed for all sims) from: {mask_path}")
        ds = xr.open_dataset(mask_path)
        pop_frac = ds['frac_L1_urban_cluster'] + ds['frac_L1_urban_centre']
        mask = (pop_frac > 0).values
        tag = 'urbanonly'
    else:
        raise ValueError(f"Unknown mask_kind: {mask_kind!r}")

    print(f"{mask_kind} mask before lat filter: {int(mask.sum())} / {mask.size} cells "
          f"({100*mask.sum()/mask.size:.2f}%)")

    # Apply the >= LAT_MIN_NORTH latitude filter using the CRCM6 geographic lat.
    lat2d = xr.open_dataset(CRCM6_REF_NC)['lat'].values
    if lat2d.shape != mask.shape:
        raise ValueError(f"lat2d shape {lat2d.shape} != mask shape {mask.shape}")
    mask = mask & (lat2d > LAT_MIN_NORTH)
    print(f"{mask_kind} mask after lat > {LAT_MIN_NORTH} deg filter: "
          f"{int(mask.sum())} / {mask.size} cells "
          f"({100*mask.sum()/mask.size:.2f}%)")
    return mask, tag


def main(iyear, sim, wetdays, future, quantile, mask_kind):

    base = '/home/vdemeyer/projects/rrg-gachon/vdemeyer'

    future_hist_sim = {'UBG': 'UBD', 'UBH': 'UBE', 'UBI': 'UBF'}

    quantile_value = quantile / 100.0
    quantile_tag = {99.0: '99', 99.9: '999'}[quantile]

    # Load percentile thresholds (once)
    percentile_pr = selection_percentile(sim, future_hist_sim, 'pr', wetdays=wetdays, future=future)
    percentile_wind = selection_percentile(sim, future_hist_sim, 'ws', wetdays=wetdays, future=future)

    # Use method='nearest' to avoid floating-point mismatches (e.g. 99.9/100 = 0.9990000000000001)
    threshold_pr = percentile_pr.pr.sel(quantile=quantile_value, method='nearest')
    threshold_wind = percentile_wind.surf_wind.sel(quantile=quantile_value, method='nearest')

    # Load the spatial mask. Both the land mask and the DEGURBA urban mask are
    # only defined on the CRCM6 rotated-pole grid, so sim='ERA5' is not supported.
    if sim == 'ERA5':
        raise RuntimeError(
            f"No '{mask_kind}' mask is available for ERA5. "
            f"Processing cannot continue for sim='ERA5'."
        )
    land_mask, mask_tag = load_spatial_mask(mask_kind, sim, future_hist_sim, base)

    # Accumulation dictionaries
    storm_cum_pr = {}
    storm_count_pr = {}
    storm_cum_wind = {}
    storm_count_wind = {}

    for imonth in [f"{imonth:02d}" for imonth in range(1, 13)]:

        print(f"Processing {sim} for iyear {iyear} and imonth {imonth}")

        last_day = calendar.monthrange(iyear, int(imonth))[1]

        if sim != 'ERA5' and iyear == 1979 and imonth == '09':
            start = f"{iyear}-{imonth}-01 01:00:00"
        else:
            start = f"{iyear}-{imonth}-01 00:00:00"

        if iyear == 2100 and imonth == '12':
            end = f"{iyear}-{imonth}-30 23:00:00"
        else:
            end = f"{iyear}-{imonth}-{last_day} 23:00:00"

        expected_time = pd.date_range(
            start=start,
            end=end,
            freq="h"
        ).to_numpy()

        ### PRECIPITATION
        if sim == 'ERA5':
            if iyear == 2023 and imonth in ['09', '10', '11', '12']: continue
            input_dir = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/ERA5/PR'
            filenames_precip = sorted(glob(f'{input_dir}/{iyear}/{imonth}/*.nc4'))
            ds_precip = xr.open_mfdataset(filenames_precip, combine='by_coords')
            ds_precip = ds_precip.sel(time=slice(f'{iyear}-{imonth}-01', f'{iyear}-{imonth}-{last_day}'))
            ds_precip = ds_precip.assign_coords({'longitude': (((ds_precip['longitude'] + 180) % 360) - 180)})
            ds_precip = ds_precip.sortby(ds_precip['longitude'])
            mask = xr.open_dataarray('/home/vdemeyer/projects/rrg-gachon/vdemeyer/ALL/MASK/mask_CRCM6_grid_for_ERA5.nc')
            ds_precip = ds_precip.where(mask, drop=True)
            ds_precip = ds_precip.rename({'tp': 'pr'})
            ds_precip['pr'] = ds_precip.pr * 1000.
            ds_precip = ds_precip.chunk({'latitude': 50, 'longitude': 50, 'time': 25})
        else:
            if (iyear == 1979 and imonth in ['01', '02', '03', '04', '05', '06', '07', '08']) or (iyear == 2098 and imonth in ['05', '06', '07', '08', '09', '10', '11', '12'] and sim == 'UBI'): continue
            filenames_precip = braced_glob(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/PR/pr_{sim.lower()}_{iyear}{imonth}_se.nc')
            ds_precip = xr.open_mfdataset(filenames_precip)
            ds_precip['time'] = ds_precip['time'].dt.floor('h')
            ds_precip['pr'] = ds_precip.pr * 3600.
            if iyear == 1979 and imonth == '09':
                expected_start_time = '1979-09-01 01:00:00'
                ds_precip = ds_precip.isel(time=slice(1, None))
            else:
                expected_start_time = f'{iyear}-{imonth}-01 00:00:00'
            actual_start_time_precip = ds_precip['time'][0].dt.strftime('%Y-%m-%d %H:%M:%S').values
            if actual_start_time_precip != expected_start_time:
                raise ValueError(f"The first time coordinate for precipitation is not {expected_start_time} but {actual_start_time_precip}")
            ds_precip = ds_precip.chunk({'rlat': 50, 'rlon': 50, 'time': 25})

        if not np.array_equal(ds_precip['time'].to_numpy(), expected_time):
            raise ValueError(f"The time coordinates for precipitation is wrong for {iyear}-{imonth}")
        
        ds_precip = ds_precip.compute()

        ### WIND
        if sim == 'ERA5':
            input_dir = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/ERA5/WIND/Magnitude'
            filenames_wind = sorted(glob(f'{input_dir}/{iyear}/{imonth}/*.nc4'))
            ds_wind = xr.open_mfdataset(filenames_wind, combine='by_coords')
            ds_wind = ds_wind.sel(time=slice(f'{iyear}-{imonth}-01', f'{iyear}-{imonth}-{last_day}'))
            ds_wind = ds_wind.assign_coords({'longitude': (((ds_wind['longitude'] + 180) % 360) - 180)})
            ds_wind = ds_wind.sortby(ds_wind['longitude'])
            ds_wind = ds_wind.where(mask, drop=True)
            ds_wind = ds_wind.chunk({'latitude': 50, 'longitude': 50, 'time': 25})
        else:
            filenames_wind = braced_glob(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/WIND/wind10_{sim.lower()}_{iyear}{imonth}_se.nc')
            ds_wind = xr.open_mfdataset(filenames_wind)
            ds_wind['time'] = ds_wind['time'].dt.round('h')
            if sim in ['UBG', 'UBH', 'UBI'] and iyear == 2100 and imonth == '12':
                ds_wind = ds_wind.isel(time=slice(0, -1)) #There is one hour of data on 2100-12-31T00:00:00.000000000 that does not exist in the precipitation file
            actual_start_time_wind = ds_wind['time'][0].dt.strftime('%Y-%m-%d %H:%M:%S').values
            if actual_start_time_wind != expected_start_time:
                raise ValueError(f"The first time coordinate for wind is not {expected_start_time} but {actual_start_time_wind}")
            ds_wind = ds_wind.chunk({'rlat': 50, 'rlon': 50, 'time': 25})

        if not np.array_equal(ds_wind['time'].to_numpy(), expected_time):
            print(ds_wind['time'].to_numpy()[:10])
            print(expected_time[:10])
            raise ValueError(f"The time coordinates for wind is wrong for {iyear}-{imonth}")
        
        ds_wind = ds_wind.compute()

        ### STORMS
        id_file = f'{base}/{sim}/STORM_RELATED/ID_1000KM/storm_id_{sim.lower()}_{iyear}{imonth}_1000km_1000hPa.nc'
        ds_id = xr.open_dataset(id_file)

        # Compute exceedance above 99th percentile
        excess_pr = (ds_precip.pr - threshold_pr).values       # (time, rlat, rlon) or (time, lat, lon)
        excess_wind = (ds_wind.surf_wind - threshold_wind).values
        storm_ids = ds_id.storm_id.values   # (time, rlat, rlon) - closest storm only

        exceed_mask_pr = (excess_pr > 0) & land_mask[np.newaxis, :, :]
        excess_pr_pos = np.where(exceed_mask_pr, excess_pr, 0.0)

        exceed_mask_wind = (excess_wind > 0) & land_mask[np.newaxis, :, :]
        excess_wind_pos = np.where(exceed_mask_wind, excess_wind, 0.0)

        # Accumulate per storm ID
        valid = ~np.isnan(storm_ids)
        unique_ids = np.unique(storm_ids[valid])

        for sid in unique_ids:
            sid_key = int(sid)
            sid_mask = (storm_ids == sid)

            # Precipitation
            pr_exceed = sid_mask & exceed_mask_pr
            storm_cum_pr[sid_key] = storm_cum_pr.get(sid_key, 0.0) + float(np.sum(excess_pr_pos[pr_exceed]))
            storm_count_pr[sid_key] = storm_count_pr.get(sid_key, 0) + int(np.sum(pr_exceed))

            # Wind
            wind_exceed = sid_mask & exceed_mask_wind
            storm_cum_wind[sid_key] = storm_cum_wind.get(sid_key, 0.0) + float(np.sum(excess_wind_pos[wind_exceed]))
            storm_count_wind[sid_key] = storm_count_wind.get(sid_key, 0) + int(np.sum(wind_exceed))

        ds_precip.close()
        ds_wind.close()
        ds_id.close()
        del excess_pr, excess_wind, storm_ids, excess_pr_pos, excess_wind_pos
        gc.collect()

    # Build output DataFrame
    all_storms = sorted(set(storm_cum_pr.keys()) | set(storm_cum_wind.keys()))

    records = []
    for sid in all_storms:
        records.append({
            'storm_id': sid,
            'cum_excess_pr': storm_cum_pr.get(sid, 0.0),
            'count_exceed_pr': storm_count_pr.get(sid, 0),
            'cum_excess_wind': storm_cum_wind.get(sid, 0.0),
            'count_exceed_wind': storm_count_wind.get(sid, 0),
        })

    df = pd.DataFrame(records)

    # Save output
    add_file = ''
    if wetdays:
        add_file += '_wetdays'
    if future and sim in future_hist_sim:
        add_file += '_future_percentile'

    # Filename carries the `mask_tag` (e.g. 'landonly' or 'urbanonly_DEGURBAE1995')
    # so the mask choice -- and, for urban, the DEGURBA epoch -- is traceable.
    output_dir = f'{base}/{sim}/STORM_RELATED/STORM_METRICS/'
    os.makedirs(output_dir, exist_ok=True)
    output_file = f'{output_dir}/storm_exceed_{quantile_tag}_metrics_{mask_tag}_{sim}_{iyear}{add_file}.pkl'
    df.to_pickle(output_file)
    print(f"\nSaved {len(df)} storms to {output_file}")
    print(df)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Per-storm exceedance metrics above a given percentile')
    parser.add_argument('iyear', type=int, help='The year for which to process')
    parser.add_argument('--sim', type=str, required=True, help='Name of the simulation')
    parser.add_argument('--quantile', type=float, required=True, choices=[99.0, 99.9], help='Percentile threshold: 99 or 99.9')
    parser.add_argument('--wetdays', action='store_true', help='Use percentile calculated on wet days only for precipitation')
    parser.add_argument('--future', action='store_true', help='Use percentile calculated on future period for future simulations')
    parser.add_argument('--mask', type=str, required=True, choices=['land', 'urban'],
                        help="Spatial mask to apply before counting exceedances: "
                             "'land' = CRCM6 sftlf>0, 'urban' = DEGURBA populated-land "
                             "(urban cluster + urban centre fraction > 0).")

    args = parser.parse_args()
    main(args.iyear, args.sim, args.wetdays, args.future, args.quantile, args.mask)

# run /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/storm_percentile_metrics.py 1985 --sim UBD --quantile 99.9 --mask land
# run /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/storm_percentile_metrics.py 1985 --sim UBD --quantile 99.9 --mask urban