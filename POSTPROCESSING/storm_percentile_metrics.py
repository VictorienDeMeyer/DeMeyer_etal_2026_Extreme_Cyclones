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
  - cum_excess_pr / cum_excess_wind: cumulative exceedance above the 99th percentile
      (sum over land grid-point-hours where pr/wind > 99th percentile within 1000km of the storm)
  - count_exceed_pr / count_exceed_wind: number of land grid-point-hours exceeding the threshold

Storms crossing year boundaries (e.g. Dec 30 to Jan 12) will appear in BOTH years' outputs
with partial cum/count values that can be summed in post-processing.
Storms are attributed to grid points via the closest-storm assignment.
Only grid points with land fraction > 0% (sftlf > 0) are included.

Author: Dr Victorien De Meyer
Year: 2026
"""

def braced_glob(path):
    l = []
    for x in braceexpand(path):
        l.extend(glob(x))          
    return l

def selection_percentile(sim, future_hist_sim, variable, wetdays=True, future=True):
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

def main(iyear, sim, wetdays, future):

    base = '/home/vdemeyer/projects/rrg-gachon/vdemeyer'

    future_hist_sim = {'UBG': 'UBD', 'UBH': 'UBE', 'UBI': 'UBF'}

    # Load percentile thresholds (once)
    percentile_pr = selection_percentile(sim, future_hist_sim, 'pr', wetdays=wetdays, future=future)
    percentile_wind = selection_percentile(sim, future_hist_sim, 'ws', wetdays=wetdays, future=future)

    threshold_pr = percentile_pr.pr.sel(quantile=0.999)
    threshold_wind = percentile_wind.surf_wind.sel(quantile=0.999)

    # Load land-sea mask: only keep grid points with > 0% land
    if sim == 'ERA5':
        raise RuntimeError(
            "No land mask is available for ERA5. Processing cannot continue for sim='ERA5'."
        )
    else:
        ds_lsm = xr.open_dataset(f'{base}/LAND_SEA_MASK/CRCM6_lsmsk.nc4')
        land_mask = (ds_lsm.sftlf.squeeze() > 0).values  # 2D boolean (rlat, rlon)

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
            mask = xr.open_dataarray('/home/vdemeyer/projects/rrg-gachon/vdemeyer/MASK/mask_CRCM6_grid_for_ERA5.nc')
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
        id_file = f'{base}/{sim}/STORM_ID_1000KM/storm_id_{sim.lower()}_{iyear}{imonth}_1000km_1005hPa.nc'
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

    output_dir = f'{base}/TRACKING/KATJA/OUTPUTS/{sim}/STORM_METRICS/'
    os.makedirs(output_dir, exist_ok=True)
    output_file = f'{output_dir}/storm_exceed_999_metrics_landonly_{sim}_{iyear}{add_file}.pkl'
    df.to_pickle(output_file)
    print(f"\nSaved {len(df)} storms to {output_file}")
    print(df)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Per-storm exceedance metrics above the 99th percentile')
    parser.add_argument('iyear', type=int, help='The year for which to process')
    parser.add_argument('--sim', type=str, required=True, help='Name of the simulation')
    parser.add_argument('--wetdays', action='store_true', help='Use percentile calculated on wet days only for precipitation')
    parser.add_argument('--future', action='store_true', help='Use percentile calculated on future period for future simulations')

    args = parser.parse_args()
    main(args.iyear, args.sim, args.wetdays, args.future)

# run /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/storm_percentile_metrics.py 1985 --sim UBD --future
