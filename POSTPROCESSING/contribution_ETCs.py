import xarray as xr
from glob import glob
from braceexpand import braceexpand
import argparse
import time

"""
Script to calculate the contribution of (E)ETCs to total (extreme) precipitation and wind. It doesn't take into account compound EETCs (see EETCs_1000km.py).
It can be run in parallel for different years and simulations (see submit_contribution_ETCs.sh).
It requires the concat_contribution_ETCs.py script to calculate the total contribution from all the yearly simulation files into a single file for the full period and all simulation.

Author: Dr Victorien De Meyer
"""

def braced_glob(path):
    files = []
    for expanded_path in braceexpand(path):
        files.extend(glob(expanded_path))
    return files

def selection_percentile(sim, future_hist_sim, variable, wetdays=True, future=True, original_selection=False):
    """
    Return an xarray Dataset for the requested percentile file.
    Parameters:
    - sim: str, name of the simulation
    - future_hist_sim: dict, mapping of future simulations to their historical counterparts 
    - variable: str, either 'pr' for precipitation or 'wind' for wind
    - wetdays: bool, whether to consider wet days only (default True)
    - future: bool, whether to consider future period (default True)
    - original_selection: bool, whether to use original selection criteria (default False)
    """
    base_dir = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/'
    settings = {
        'pr': {'dir': 'PR_Percentile', 'prefix': 'pr'},
        'ws': {'dir': 'WIND_Percentile', 'prefix': 'surf_wind'}
    }
    var_dir, prefix = settings[variable]['dir'], settings[variable]['prefix']

    if original_selection:
        """
        On utilise les centiles avec laquelle les sélections originales des EETCs ont été faites. Les centiles ont été calculés
        sur toute la période historique disponible des jeux de données, c-à-d 1979-2014 pour les simulations 
        historiques, 1979-2023 pour UBB et 1979-082023 pour ERA5.
        """
        base_sim = future_hist_sim.get(sim, sim)
        filename = f"{prefix}_{base_sim}_percentile.nc"
    else:
        base_sim = sim if future else future_hist_sim.get(sim, sim)
        wetdays_str = '_wetdays' if (wetdays and variable == 'pr') else ''
        period = (
            '2063-2097' if future and sim in future_hist_sim
            else '1980-2014'
        )
        # period = (
        #     '2058-2082' if future and sim in future_hist_sim
        #     else '1980-2004'
        # )
        filename = f"{prefix}_{base_sim.lower()}_percentile_{period}{wetdays_str}.nc"

    file_path = f"{base_dir}{base_sim}/{var_dir}/{filename}"

    print(f"\nLoading percentile file: {file_path}\n")

    percentile = xr.open_dataset(file_path)

    if original_selection and variable == 'pr' and sim != 'ERA5':
        percentile['pr'] = percentile.pr * 3600.  #original percentiles were not in mm/h

    return percentile

def main(year, sim, var, wetdays, future, original_selection, add_file):

########################### INITIALISATION #########################################
    hist_future_map = {'UBG': 'UBD', 'UBH': 'UBE', 'UBI': 'UBF'}

    if sim in hist_future_map:
        hist_sim = hist_future_map[sim]

    if sim == 'ERA5':
        var_lat = 'latitude'
        var_lon = 'longitude'
    else:
        var_lat = 'rlat'
        var_lon = 'rlon'

    if var == 'pr':
        name_var = 'pr'
        folder_var = 'PR'
        file_var = 'pr'
    elif var == 'ws':
        name_var = 'surf_wind'
        if sim == 'ERA5':
            folder_var = 'WIND/Magnitude'
        else:
            folder_var = 'WIND'
        file_var = 'wind10'

############################ CALCULATION ######################################

    ### Chargement des données
    if sim == 'ERA5':
        mask = xr.open_dataarray('/home/vdemeyer/projects/rrg-gachon/vdemeyer/ALL/MASK/mask_CRCM6_grid_for_ERA5.nc')
        if var == 'pr':
            input_dir = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/ERA5/PR'
            filenames_var = sorted(glob(f'{input_dir}/{year}/*/*.nc4'))
        elif var == 'ws':
            input_dir = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/ERA5/WIND/Magnitude'
            filenames_var = sorted(glob(f'{input_dir}/{year}/*/*.nc4'))
        ds_var = xr.open_mfdataset(filenames_var, combine='by_coords')
        ds_var = ds_var.sel(time=slice(f'{year}-01-01', f'{year}-12-31'))
        ds_var = ds_var.assign_coords({'longitude': (((ds_var['longitude'] + 180) % 360) - 180)})
        ds_var = ds_var.sortby(ds_var['longitude'])
        ds_var = ds_var.where(mask, drop=True)
        if var == 'pr':
            ds_var = ds_var.rename({'tp': 'pr'})
            ds_var['pr'] = ds_var.pr * 1000.
    else:
        filenames_var = braced_glob(f"/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{folder_var}/{file_var}_{sim.lower()}_{year}*_se.nc") ############################
        ds_var = xr.open_mfdataset(
            filenames_var,
            combine="by_coords",        
            data_vars="minimal",        # n'empile que les vraies variables de données
            coords="minimal",           # n'empile pas 36 fois la même grille
            compat="override",          # évite les conflits inutiles si les attrs diffèrent
        )
        if var == 'pr':
            ds_var = ds_var.drop_vars(['rotated_pole', 'time_bnds']).squeeze('height', drop=True)
            ds_var['time'] = ds_var['time'].dt.floor('h')
            ds_var['pr'] = ds_var['pr'] * 3600
        elif var == 'ws':
            ds_var['time'] = ds_var['time'].dt.round('h')
            if sim in hist_future_map and year == 2100:
                ds_var = ds_var.isel(time=slice(0, -1)) #There is one hour of data on 2100-12-31T00:00:00.000000000 that does not exist in the precipitation file
    ds_var = ds_var.chunk({var_lat: -1, var_lon: -1, 'time': 100})
        
    filenames_ETCs = braced_glob(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/STORM_RELATED/ID_1000KM/storm_id_{sim.lower()}_{year}*_1000km_1000hPa.nc')
    ds_ETCs = xr.open_mfdataset(filenames_ETCs)
    ds_ETCs = ds_ETCs.chunk({var_lat: -1, var_lon: -1, 'time': 100})

    percentile = selection_percentile(sim, hist_future_map, var, wetdays=wetdays, future=future, original_selection=original_selection)
    
    ### Calcul
    mask_var_ext = ds_var[[name_var]].where(ds_var[name_var] >= percentile[name_var])
    mask_var_ext['season'] = mask_var_ext['time'].dt.season
    ds_var['season'] = ds_var['time'].dt.season

    # Précip/vent extrême (>= centile) ET à moins de 1000km d'un ETC
    mask_ETCs_ext = ds_var[[name_var]].where(ds_ETCs['storm_id'].notnull() & (ds_var[name_var] >= percentile[name_var]))
    mask_ETCs_ext['season'] = mask_ETCs_ext['time'].dt.season

    # Précip/vent à moins de 1000km d'un ETC
    mask_ETCs = ds_var[[name_var]].where(ds_ETCs['storm_id'].notnull())
    mask_ETCs['season'] = mask_ETCs['time'].dt.season

    for season in ['DJF', 'MAM', 'JJA', 'SON']:
        start_time = time.time()
        print(f"Calculating for {season}")
        
        #Total rainfall/wind greater than the percentile threshold
        mask_var_ext_season = mask_var_ext.where(mask_var_ext['season'] == season, drop=True)
        sum = mask_var_ext_season[name_var].sum(dim='time', skipna=True)
        count = mask_var_ext_season.where(mask_var_ext_season[name_var] > 0.)[name_var].count(dim='time')
        sum = sum.expand_dims({'season': [season], 'year': [year]})
        count = count.expand_dims({'season': [season], 'year': [year]})
        if sim == 'ERA5':
            sum = sum.where(mask, drop=True)
            count = count.where(mask, drop=True)
        sum.to_netcdf(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{folder_var}/1000km_storm/total_{file_var}_ext_{sim.lower()}_1000hPa_{season}_{year}{add_file}.nc')
        count.to_netcdf(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{folder_var}/1000km_storm/count_{file_var}_ext_{sim.lower()}_1000hPa_{season}_{year}{add_file}.nc')
        
        two_time = time.time()
        print('First two files saved in {:.2f} seconds'.format(two_time - start_time))

        #Total rainfall/wind
        ds_var_season = ds_var.where(ds_var['season'] == season, drop=True)
        sum = ds_var_season[name_var].sum(dim='time', skipna=True)
        count = ds_var_season[name_var].where(ds_var_season[name_var] > 0).count(dim='time')
        sum = sum.expand_dims({'season': [season], 'year': [year]})
        count = count.expand_dims({'season': [season], 'year': [year]})
        if sim == 'ERA5':
            sum = sum.where(mask, drop=True)
            count = count.where(mask, drop=True)
        sum.to_netcdf(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{folder_var}/1000km_storm/total_{file_var}_{sim.lower()}_1000hPa_{season}_{year}.nc')
        count.to_netcdf(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{folder_var}/1000km_storm/count_{file_var}_{sim.lower()}_1000hPa_{season}_{year}.nc')
        
        three_time = time.time()
        print('Second two files saved in {:.2f} seconds'.format(three_time - two_time))
        
        #Total rainfall/wind greater than the percentile threshold and within 1000km of an ETC (hence an EETC if total > 0)
        mask_ETCs_ext_season = mask_ETCs_ext.where(mask_ETCs_ext['season'] == season, drop=True) #le cumul au dessus du seuil, quand on est à - de 1000km d'un ETC, pour la saison season
        sum = mask_ETCs_ext_season[name_var].sum(dim='time', skipna=True)
        count = mask_ETCs_ext_season.where(mask_ETCs_ext_season[name_var] > 0.)[name_var].count(dim='time')
        sum = sum.expand_dims({'season': [season], 'year': [year]})
        count = count.expand_dims({'season': [season], 'year': [year]})
        if sim == 'ERA5':
            sum = sum.where(mask, drop=True)
            count = count.where(mask, drop=True)
        sum.to_netcdf(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{folder_var}/1000km_storm/total_{file_var}_ext_{sim.lower()}_1000hPa_1000km_extreme_storm_{season}_{year}{add_file}.nc')
        count.to_netcdf(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{folder_var}/1000km_storm/count_{file_var}_ext_{sim.lower()}_1000hPa_1000km_extreme_storm_{season}_{year}{add_file}.nc')
        
        fourth_time = time.time()
        print('Third two files saved in {:.2f} seconds'.format(fourth_time - three_time))

        #Total rainfall/wind within 1000km of an ETC
        mask_ETCs_season = mask_ETCs.where(mask_ETCs['season'] == season, drop=True)
        sum = mask_ETCs_season[name_var].sum(dim='time', skipna=True)
        count = mask_ETCs_season.where(mask_ETCs_season[name_var] > 0.)[name_var].count(dim='time')
        sum = sum.expand_dims({'season': [season], 'year': [year]})
        count = count.expand_dims({'season': [season], 'year': [year]})
        if sim == 'ERA5':
            sum = sum.where(mask, drop=True)
            count = count.where(mask, drop=True)
        sum.to_netcdf(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{folder_var}/1000km_storm/total_{file_var}_{sim.lower()}_1000hPa_1000km_storm_{season}_{year}.nc')
        count.to_netcdf(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{folder_var}/1000km_storm/count_{file_var}_{sim.lower()}_1000hPa_1000km_storm_{season}_{year}.nc')
        
        fifth_time = time.time()
        print('Fourth two files saved in {:.2f} seconds'.format(fifth_time - fourth_time))

        end_time = time.time()
        print(f"Time taken for {season}: {end_time - start_time:.2f} seconds")


    print(f"NetCDF files for {sim} and {var} saved")

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description='Calculate contribution of ETCs and EETCs to total precipitation and wind')
    parser.add_argument('year', type=int, help='The year for which to calculate the statistics')
    parser.add_argument('--sim', type=str, required=True, help='Name of the simulation')
    parser.add_argument('--var', type=str, help='Variable to process (pr or ws)')
    parser.add_argument('--wetdays', action='store_true', help='Computation done with percentile calculated on wet days only for precipitation')
    parser.add_argument('--future', action='store_true', help='Computation done with percentile calculated on future period for future simulations')
    parser.add_argument('--original_selection', action='store_true', help='Use original selection criteria, with percentiles calculated on the full historical period')

    args = parser.parse_args()

    year = args.year
    sim = args.sim
    var = args.var
    wetdays = args.wetdays
    future = args.future
    original_selection = args.original_selection

    add_file = ''
    if original_selection and (wetdays or future):
        raise ValueError("original_selection cannot be combined with wetdays or future")
    if not original_selection:
        if wetdays:
            add_file += '_wetdays'
        if future and sim in ['UBG', 'UBH', 'UBI']:
            add_file += '_future_percentile'

    main(year, sim, var, wetdays, future, original_selection, add_file)

# run /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/contribution_ETCs.py 2019 --sim UBB --var pr --future