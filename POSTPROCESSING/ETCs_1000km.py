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
This script generates a NetCDF file of precipitation and wind data within 1000 km of storm trajectories.
For extreme, it doesn't take into account compound EETCs only (see EETCs_list), so EETCs for precipitation are not necessarily EETCs for wind.
This script processes data for a specified year, simulation and with or without extreme mode, and can be run in parallel (see submit_ETCs_1000km.sh).
As it is, the extreme mode will generate NetCDF files with precipitation and wind within 1000 km of EETCs, with EETCs defined in South Quebec (see EETCs_stat.py). But it is not very useful.

Author: Dr Victorien De Meyer
Year: 2025
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
    
    Used to calculate distance between storm center and grid points
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    km = 6367 * c
    return km


def main(iyear, sim, ext, wetdays, future, original_selection, add_file):

    if ext == True:

        print('mode extreme: activated')

        df, EETC_dict = open_files(sim, metric='diff', wetdays=wetdays, future=future, original_selection=original_selection, period_filtering=False)
        
        quantiles = [0.98, 0.99, 0.995, 0.999]

        EETCs_list = {'precip': {'0.98': [], '0.99': [], '0.995': [], '0.999': []},
              'wind': {'0.98': [], '0.99': [], '0.995': [], '0.999': []}}

        for storm in EETC_dict:
            for quantile in quantiles:
                if (
                    EETC_dict[storm]['cum_precip'].sel(quantile=quantile).values > 1 or #!=0 if test='diff'!
                    EETC_dict[storm]['cum_avg_precip'].sel(quantile=quantile).values > 1
                ):
                    EETCs_list['precip'][str(quantile)].append(storm)
                if (
                    EETC_dict[storm]['cum_wind'].sel(quantile=quantile).values > 1 or
                    EETC_dict[storm]['cum_avg_wind'].sel(quantile=quantile).values > 1 or
                    EETC_dict[storm]['SSI'].sel(quantile=quantile).values != 0 #always != 0
                ):
                    EETCs_list['wind'][str(quantile)].append(storm)
    else:
        df, _ = open_files(sim, metric='diff', wetdays=wetdays, future=future, original_selection=original_selection, period_filtering=False)

    df = df[df['date'].dt.year == iyear]

    for imonth in [f"{month:02d}" for month in range(1, 13)]:

        print(f"Processing {sim} for year {iyear} and month {imonth}")

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
            # filenames_precip = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/ERA5/PR/era5_tp_CORDEX_NA_1979-2023.zarr'
            # ds_precip = xr.open_zarr(filenames_precip)
            # ds_precip = ds_precip.sel(time=slice(f'{iyear}-{imonth}-01', f'{iyear}-{imonth}-{last_day}'))
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

        if hasattr(ds_precip, 'lon'):
            var_lon, var_lat = 'lon', 'lat'
        elif hasattr(ds_precip, 'longitude'):
            var_lon, var_lat = 'longitude', 'latitude'
        else:
            raise AttributeError(f'No dimension lon or longitude / lat or latitude in {ds_precip}')

        ### WIND
        if sim == 'ERA5':
            # filenames_wind = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/ERA5/WIND/Magnitude/era5_wind10_CORDEX_NA_1979-2023.zarr'
            # ds_wind = xr.open_zarr(filenames_wind)
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

        filtered_precip_list = []
        filtered_wind_list = []

        if sim == 'ERA5':
            lon_2d, lat_2d = np.meshgrid(ds_precip[var_lon].values, ds_precip[var_lat].values)
            if ext == True:
                shape_grid = xr.DataArray(np.expand_dims(lon_2d, axis=-1).repeat(len(quantiles), axis=-1), 
                        dims=[var_lat, var_lon, 'quantile'], 
                        coords={var_lon: ds_precip[var_lon], var_lat: ds_precip[var_lat], 'quantile': quantiles}) 
            else:
                shape_grid = xr.DataArray(lon_2d, dims=[var_lat, var_lon], coords={var_lon: ds_precip[var_lon], var_lat: ds_precip[var_lat]})
        else:
            lon_2d = ds_precip[var_lon].values
            lat_2d = ds_precip[var_lat].values
            if ext == True:
                shape_grid = ds_precip[var_lon].expand_dims(quantile=quantiles)
            else:
                shape_grid = ds_precip[var_lon]

        for itime in ds_precip['time'].values:
            
            storms_at_time = df[df['date'] == pd.Timestamp(itime)]
            
            if storms_at_time.empty:
                if ext == True:
                    filtered_precip_list.append(xr.full_like(ds_precip.sel(time=itime).pr, np.nan).expand_dims(quantile=quantiles))
                    filtered_wind_list.append(xr.full_like(ds_wind.sel(time=itime).surf_wind, np.nan).expand_dims(quantile=quantiles))
                else:
                    filtered_precip_list.append(xr.full_like(ds_precip.sel(time=itime).pr, np.nan))
                    filtered_wind_list.append(xr.full_like(ds_wind.sel(time=itime).surf_wind, np.nan))
                continue

            if ext == True:                
                for EETC_key in ['precip', 'wind']:
                    distances = xr.full_like(shape_grid, np.inf, dtype=float) #voir le notebook pour sauvegarder distances
                    for quantile in quantiles:
                        filtered_storms = storms_at_time[storms_at_time['storm'].isin(EETCs_list[EETC_key][str(quantile)])]
                        if filtered_storms.empty:
                            continue
                        storm_lons = filtered_storms['lon'].values
                        storm_lats = filtered_storms['lat'].values
                        for lon, lat in zip(storm_lons, storm_lats):
                            distances.loc[dict(quantile=quantile)] = xr.ufuncs.minimum(distances.sel(quantile=quantile), haversine(lon_2d, lat_2d, lon, lat))
                    if EETC_key == 'precip':
                        precip_mask = ds_precip.sel(time=itime).where(distances <= 1000, drop=False)
                        filtered_precip_list.append(precip_mask.pr)
                    elif EETC_key == 'wind':
                        wind_mask = ds_wind.sel(time=itime).where(distances <= 1000, drop=False)
                        filtered_wind_list.append(wind_mask.surf_wind)              

            else:
                storm_lons = storms_at_time['lon'].values
                storm_lats = storms_at_time['lat'].values
                distances = xr.full_like(shape_grid, np.inf, dtype=float)

                for lon, lat in zip(storm_lons, storm_lats):
                    distances = xr.ufuncs.minimum(distances, haversine(lon_2d, lat_2d, lon, lat))

                precip_mask = ds_precip.sel(time=itime).where(distances <= 1000, drop=False)
                wind_mask = ds_wind.sel(time=itime).where(distances <= 1000, drop=False)
                
                filtered_precip_list.append(precip_mask.pr)
                filtered_wind_list.append(wind_mask.surf_wind)
            
        filtered_precip = xr.Dataset({
            'pr': xr.concat(filtered_precip_list, dim='time')
        })
        if sim == 'ERA5': filtered_precip = filtered_precip.where(mask, drop=True)       

        output_dir = f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/PR/1000km_storm/'
        os.makedirs(output_dir, exist_ok=True)
        if ext ==True :
            filtered_precip.to_netcdf(f'{output_dir}/pr_{sim.lower()}_{iyear}{imonth}_1000km_1005hPa_extreme_storm{add_file}.nc')
        else:
            filtered_precip.to_netcdf(f'{output_dir}/pr_{sim.lower()}_{iyear}{imonth}_1000km_1005hPa_storm.nc')

        filtered_wind = xr.Dataset({
            'surf_wind': xr.concat(filtered_wind_list, dim='time')
        })
        if sim == 'ERA5': filtered_wind = filtered_wind.where(mask, drop=True)
        
        output_dir = f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/WIND/'
        output_dir += 'Magnitude/' if sim == 'ERA5' else ''
        output_dir += '1000km_storm/'
        os.makedirs(output_dir, exist_ok=True)
        if ext == True:
            filtered_wind.to_netcdf(f'{output_dir}/wind10_{sim.lower()}_{iyear}{imonth}_1000km_1005hPa_extreme_storm{add_file}.nc')
        else:
            filtered_wind.to_netcdf(f'{output_dir}/wind10_{sim.lower()}_{iyear}{imonth}_1000km_1005hPa_storm.nc')

        ds_precip.close()
        ds_wind.close()
        filtered_precip.close()
        filtered_wind.close()
        del ds_precip, ds_wind, filtered_precip, filtered_wind, filtered_precip_list, filtered_wind_list
        gc.collect()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Precipitation from within 1000 km of storm trajectories')
    parser.add_argument('iyear', type=int, help='The year for which to calculate the statistics')
    parser.add_argument('--sim', type=str, required=True, help='Name of the simulation')
    parser.add_argument('--wetdays', action='store_true', help='Computation done with percentile calculated on wet days only for precipitation')
    parser.add_argument('--future', action='store_true', help='Computation done with percentile calculated on future period for future simulations')
    parser.add_argument('--original_selection', action='store_true', help='Use original selection criteria, with percentiles calculated on the full historical period')
    parser.add_argument('--ext', action='store_true', help='Activate extreme mode to process EETCs only')

    args = parser.parse_args()

    iyear = args.iyear
    sim = args.sim
    wetdays = args.wetdays
    future = args.future
    original_selection = args.original_selection
    ext = args.ext

    add_file = ''
    if original_selection and (wetdays or future):
        raise ValueError("original_selection cannot be combined with wetdays or future")
    if not original_selection:
        if wetdays:
            add_file += '_wetdays'
        if future and sim in ['UBG', 'UBH', 'UBI']:
            add_file += '_future_percentile'

    main(iyear, sim, ext, wetdays, future, original_selection, add_file)

# run /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/ETCs_1000km.py 2100 --sim UBG --future --ext 
