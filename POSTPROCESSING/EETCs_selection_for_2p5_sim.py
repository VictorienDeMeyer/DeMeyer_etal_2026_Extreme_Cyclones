import pickle
import xarray as xr
import pandas as pd
from glob import glob
from braceexpand import braceexpand
import numpy as np
import os
from tqdm import tqdm
import argparse

def braced_glob(path):
    l = []
    for x in braceexpand(path):
        l.extend(glob(x))          
    return l

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    Possible and slightly more precise with geopy or pyproj through xr.apply_ufunc but longer
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

def main(sim, output_file, endyear):

    hist_future_map = {'UBG': 'UBD', 'UBH': 'UBE', 'UBI': 'UBF'}

    if sim in hist_future_map:
        hist_sim = hist_future_map[sim]

    df = pd.read_csv(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/{sim}_psl_smooth_400km_12h_1000hPa.txt',
                        sep=r' ', header=0, engine='python', names=['storm','point','i','j','date','lat','lon','pressure'])
    df['date'] = pd.to_datetime(df['date'])

    with open(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/EETC/EETC_cum_{sim}_Quebec_1000hPa_1979-{endyear}_compound_8hrs_quantile_SSI.pkl', 'rb') as pickle_file:
        EETC_dict = pickle.load(pickle_file)

    if sim in hist_future_map:
        percentile_precip = xr.open_dataset(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{hist_sim}/PR_Percentile/pr_{hist_sim.lower()}_percentile.nc')
    else:
        percentile_precip = xr.open_dataset(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/PR_Percentile/pr_{sim.lower()}_percentile.nc')
    if sim != 'ERA5': percentile_precip['pr'] = percentile_precip.pr * 3600.
    percentile_precip = percentile_precip.sel(quantile=[0.999])

    if sim in hist_future_map:
        percentile_wind = xr.open_dataset(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{hist_sim}/WIND_Percentile/surf_wind_{hist_sim.lower()}_percentile.nc')
    else:
        percentile_wind = xr.open_dataset(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/WIND_Percentile/surf_wind_{sim.lower()}_percentile.nc')
    percentile_wind = percentile_wind.sel(quantile=[0.999])
    percentile_wind['surf_wind'] = percentile_wind.surf_wind * 3.6

    west_lon = -80
    east_lon = -66
    north_lat = 55
    south_lat = 44

    if sim == 'ERA5':
        percentile_precip = percentile_precip.sel({'longitude': slice(west_lon, east_lon), 'latitude': slice(north_lat, south_lat)})
        percentile_wind = percentile_wind.sel({'longitude': slice(west_lon, east_lon), 'latitude': slice(north_lat, south_lat)})

    else:
        mask = (
            (percentile_precip.lon >= west_lon) &
            (percentile_precip.lon <= east_lon) &
            (percentile_precip.lat >= south_lat) &
            (percentile_precip.lat <= north_lat)
        )

        percentile_precip = percentile_precip.where(mask, drop=True)
        percentile_wind = percentile_wind.where(mask, drop=True)

    coord_lon = 'longitude' if sim == 'ERA5' else 'lon'
    coord_lat = 'latitude' if sim == 'ERA5' else 'lat'

    all_storms_df = pd.DataFrame()

    for id_storm in tqdm(EETC_dict):

        if EETC_dict[id_storm]['cum_precip'].sel(quantile=0.999).values > 0 and EETC_dict[id_storm]['cum_wind'].sel(quantile=0.999).values > 0:

            iEETC = df.groupby('storm').get_group(id_storm)

            month_years = iEETC['date'].dt.to_period('M').unique()

            if sim == 'ERA5':
                filenames_precip = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/ERA5/PR/era5_tp_CORDEX_NA_1979-2023.zarr'
                ds_precip = xr.open_mfdataset(filenames_precip)
                ds_precip = ds_precip.rename({'tp': 'pr'})
                ds_precip = ds_precip.sel(time=ds_precip['time'].dt.strftime('%Y-%m').isin(month_years.astype(str)))

                filenames_wind = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/ERA5/WIND/Magnitude/era5_wind10_CORDEX_NA_1979-2023.zarr'
                ds_wind = xr.open_mfdataset(filenames_wind)
                ds_wind = ds_wind.sel(time=ds_wind['time'].dt.strftime('%Y-%m').isin(month_years.astype(str)))

            else:
                filename_precip = []
                filename_wind = []
                for period in month_years:
                    year = period.year
                    month = period.month
                    if sim in hist_future_map and year < 2015:
                        filename_precip.extend(braced_glob(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{hist_sim}/PR/pr_{hist_sim.lower()}_{year}{month:02d}_se.nc'))
                        filename_wind.extend(braced_glob(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{hist_sim}/WIND/wind10_{hist_sim.lower()}_{year}{month:02d}_se.nc'))
                    else:
                        filename_precip.extend(braced_glob(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/PR/pr_{sim.lower()}_{year}{month:02d}_se.nc'))
                        filename_wind.extend(braced_glob(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/WIND/wind10_{sim.lower()}_{year}{month:02d}_se.nc'))
                ds_precip = xr.open_mfdataset(filename_precip)
                ds_precip['time'] = ds_precip['time'].dt.floor('h')
                ds_precip['pr'] = ds_precip.pr * 3600.
                
                ds_wind = xr.open_mfdataset(filename_wind)
                ds_wind['time'] = ds_wind['time'].dt.round('h')
            ds_wind['surf_wind'] = ds_wind.surf_wind * 3.6


            mask_diff_precip = ds_precip - percentile_precip
            mask_diff_precip = mask_diff_precip.where(mask_diff_precip >= 0, np.nan)
            mask_diff_precip = mask_diff_precip.compute()
            mask_diff_wind = ds_wind - percentile_wind
            mask_diff_wind = mask_diff_wind.where(mask_diff_wind >= 0, np.nan)
            mask_diff_wind = mask_diff_wind.compute()

            itime_precip_first = None
            itime_wind_first = None
            itime_precip_last = None
            itime_wind_last = None

            for itrack, row in iEETC.iterrows():        
                ilon, ilat, itime = row['lon'], row['lat'], row['date']

                if itime_precip_first is None:
                    mask_itime_precip = mask_diff_precip.sel(time=itime).where(mask_diff_precip.sel(time=itime).map(lambda x: haversine(ilon, ilat, getattr(x, coord_lon), getattr(x, coord_lat)) <= 1000), drop=True).pr
                    if mask_itime_precip.notnull().any():
                        itime_precip_first = itime

                if itime_wind_first is None:
                    mask_itime_wind = mask_diff_wind.sel(time=itime).where(mask_diff_wind.sel(time=itime).map(lambda x: haversine(ilon, ilat, getattr(x, coord_lon), getattr(x, coord_lat)) <= 1000), drop=True).surf_wind
                    if mask_itime_wind.notnull().any():
                        itime_wind_first = itime

                if itime_precip_first is not None and itime_wind_first is not None:
                    break

            for itrack, row in iEETC.iloc[::-1].iterrows():        
                ilon, ilat, itime = row['lon'], row['lat'], row['date']

                if itime_precip_last is None:
                    mask_itime_precip = mask_diff_precip.sel(time=itime).where(mask_diff_precip.sel(time=itime).map(lambda x: haversine(ilon, ilat, getattr(x, coord_lon), getattr(x, coord_lat)) <= 1000), drop=True).pr
                    if mask_itime_precip.notnull().any():
                        itime_precip_last = itime

                if itime_wind_last is None:
                    mask_itime_wind = mask_diff_wind.sel(time=itime).where(mask_diff_wind.sel(time=itime).map(lambda x: haversine(ilon, ilat, getattr(x, coord_lon), getattr(x, coord_lat)) <= 1000), drop=True).surf_wind
                    if mask_itime_wind.notnull().any():
                        itime_wind_last = itime

                if itime_precip_last is not None and itime_wind_last is not None:
                    break

            if itime_precip_first is not None and itime_wind_first is not None and itime_precip_last is not None and itime_wind_last is not None:
                new_df = pd.DataFrame({
                    'id_storm': [id_storm],
                    'ETC_PRcum': [EETC_dict[id_storm]['cum_precip'].sel(quantile=0.999).values],
                    'ETC_PRint': [EETC_dict[id_storm]['cum_avg_precip'].sel(quantile=0.999).values],
                    'ETC_WScum': [EETC_dict[id_storm]['cum_wind'].sel(quantile=0.999).values],
                    'ETC_WSint': [EETC_dict[id_storm]['cum_avg_wind'].sel(quantile=0.999).values],
                    'ETC_SSI': [EETC_dict[id_storm]['SSI'].sel(quantile=0.999).values],
                    'compound_PR_WS': [EETC_dict[id_storm]['compound_8hrs_quantile']['99.9']],
                    'first_date_with_PRext': [itime_precip_first.strftime('%Y-%m-%d %H:%M:%S')],
                    'first_date_with_WSext': [itime_wind_first.strftime('%Y-%m-%d %H:%M:%S')],
                    'last_date_with_PRext': [itime_precip_last.strftime('%Y-%m-%d %H:%M:%S')],
                    'last_date_with_WSext': [itime_wind_last.strftime('%Y-%m-%d %H:%M:%S')]
                })

                all_storms_df = pd.concat([all_storms_df, new_df], ignore_index=True)

    all_storms_df.to_csv(output_file, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Retrieve EETC information for 2.5km simulations to be run')
    parser.add_argument('--sim', type=str, required=True, help='Name of the simulation')

    args = parser.parse_args()

    sim = args.sim

    print(f'Processing simulation: {sim}')
          
    if sim in ['UBB', 'ERA5']:
        endyear = 2023
    elif sim in ['UBG', 'UBH']:
        endyear = 2100
    elif sim == 'UBI':
        endyear = 2098
    else:
        endyear = 2014

    print(f'Processing simulation: {sim} until {endyear}')

    output_dir = f"/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS"
    output_file = f'{output_dir}/EETC_{sim}_Quebec_1979-{endyear}_per999_for_Alejandro.txt'

    if os.path.exists(output_file):
        os.remove(output_file)

    main(sim, output_file, endyear)


# run /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/EETCs_selection_for_2p5_sim.py --sim UBB