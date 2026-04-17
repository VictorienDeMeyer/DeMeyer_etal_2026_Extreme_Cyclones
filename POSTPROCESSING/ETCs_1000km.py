import xarray as xr
import pandas as pd
import numpy as np
from glob import glob
from braceexpand import braceexpand
import os
import argparse
import gc
import calendar
from ETC_tools import open_files

"""
This script generates a NetCDF file of storm IDs within 1000 km of storm trajectories.
For each grid point at each timestep, it records the closest storm ID.

Author: Dr Victorien De Meyer
Year: 2026
"""

def braced_glob(path):
    l = []
    for x in braceexpand(path):
        l.extend(glob(x))
    return l


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees).
    """
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    km = 6367 * c
    return km


def main(iyear, sim):

    df, _ = open_files(sim, period_filtering=False)
    df = df[df['date'].dt.year == iyear]

    for imonth in [f"{month:02d}" for month in range(1, 13)]:

        print(f"Processing storm IDs for {sim} year {iyear} month {imonth}")

        last_day = calendar.monthrange(iyear, int(imonth))[1]

        if sim != 'ERA5' and iyear == 1979 and imonth == '09':
            start = f"{iyear}-{imonth}-01 01:00:00"
        else:
            start = f"{iyear}-{imonth}-01 00:00:00"

        if iyear == 2100 and imonth == '12':
            end = f"{iyear}-{imonth}-30 23:00:00"
        else:
            end = f"{iyear}-{imonth}-{last_day} 23:00:00"

        expected_time = pd.date_range(start=start, end=end, freq="h")

        # Skip months with no data (same logic as ETCs_1000km.py)
        if sim == 'ERA5' and iyear == 2023 and imonth in ['09', '10', '11', '12']:
            continue
        if sim != 'ERA5' and ((iyear == 1979 and imonth in ['01', '02', '03', '04', '05', '06', '07', '08']) or
                              (iyear == 2098 and imonth in ['05', '06', '07', '08', '09', '10', '11', '12'] and sim == 'UBI')):
            continue

        # Load grid coordinates from a reference precip file
        if sim == 'ERA5':
            input_dir = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/ERA5/PR'
            filenames = sorted(glob(f'{input_dir}/{iyear}/{imonth}/*.nc4'))
            ds_ref = xr.open_dataset(filenames[0])
            ds_ref = ds_ref.assign_coords({'longitude': (((ds_ref['longitude'] + 180) % 360) - 180)})
            ds_ref = ds_ref.sortby(ds_ref['longitude'])
            mask = xr.open_dataarray('/home/vdemeyer/projects/rrg-gachon/vdemeyer/MASK/mask_CRCM6_grid_for_ERA5.nc')
            ds_ref = ds_ref.where(mask, drop=True)
            lon_2d, lat_2d = np.meshgrid(ds_ref['longitude'].values, ds_ref['latitude'].values)
            spatial_dims = ['latitude', 'longitude']
            spatial_shape = lon_2d.shape
            spatial_coords = {'latitude': ds_ref['latitude'].load(), 'longitude': ds_ref['longitude'].load()}
            ds_ref.close()
        else:
            filenames = braced_glob(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/PR/pr_{sim.lower()}_{iyear}{imonth}_se.nc')
            ds_ref = xr.open_dataset(filenames[0])
            lon_2d = ds_ref['lon'].values
            lat_2d = ds_ref['lat'].values
            spatial_dims = ['rlat', 'rlon']
            spatial_shape = lon_2d.shape
            spatial_coords = {'rlat': ds_ref['rlat'].load(), 'rlon': ds_ref['rlon'].load(), 'lon': ds_ref['lon'].load(), 'lat': ds_ref['lat'].load()}
            rotated_pole = ds_ref['rotated_pole'].load()
            rotated_pole_attrs = {attr: ds_ref.attrs[attr] for attr in
                                  ["grid_mapping_name", "grid_north_pole_latitude",
                                   "grid_north_pole_longitude", "north_pole_grid_longitude"]
                                  if attr in ds_ref.attrs}
            ds_ref.close()

        # Initialize output array (NaN = no storm within 1000km)
        n_times = len(expected_time)
        storm_id_data = np.full((n_times, *spatial_shape), np.nan, dtype=np.float32)

        for t_idx, itime in enumerate(expected_time):

            storms_at_time = df[df['date'] == pd.Timestamp(itime)]

            if storms_at_time.empty:
                continue

            storm_ids = storms_at_time['storm'].values.astype(float)
            n_storms = len(storm_ids)

            # Compute distance from each storm to each grid point
            storm_distances = np.empty((n_storms, *spatial_shape))
            for i, (_, row) in enumerate(storms_at_time.iterrows()):
                storm_distances[i] = haversine(lon_2d, lat_2d, row['lon'], row['lat'])

            # Sort storms by distance at each grid point
            sorted_indices = np.argsort(storm_distances, axis=0)
            sorted_distances = np.take_along_axis(storm_distances, sorted_indices, axis=0)

            # Fill closest storm ID
            within_mask = sorted_distances[0] <= 1000
            mapped_ids = storm_ids[sorted_indices[0]]
            storm_id_data[t_idx][within_mask] = mapped_ids[within_mask]

        # Create xarray Dataset
        coords = {
            'time': expected_time,
            **spatial_coords
        }

        ds_out = xr.Dataset({
            'storm_id': xr.DataArray(
                storm_id_data,
                dims=['time'] + spatial_dims,
                coords=coords
            )
        })

        if sim != 'ERA5':
            ds_out["rotated_pole"] = rotated_pole
            ds_out.attrs.update(rotated_pole_attrs)

        output_dir = f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/STORM_ID_1000KM/'
        os.makedirs(output_dir, exist_ok=True)
        encoding = {'storm_id': {'zlib': True, 'complevel': 9, 'dtype': 'float32'}}
        ds_out.to_netcdf(f'{output_dir}/storm_id_{sim.lower()}_{iyear}{imonth}_1000km_1000hPa.nc', encoding=encoding)

        print(f"  Saved storm IDs for {iyear}-{imonth}")

        ds_out.close()
        del storm_id_data
        gc.collect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Storm IDs within 1000 km of storm trajectories')
    parser.add_argument('iyear', type=int, help='The year for which to process')
    parser.add_argument('--sim', type=str, required=True, help='Name of the simulation')

    args = parser.parse_args()
    main(args.iyear, args.sim)

# run /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/storm_id_1000km.py 2082 --sim UBG