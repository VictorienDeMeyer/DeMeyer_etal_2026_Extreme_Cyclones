import pickle
import xarray as xr
import pandas as pd
from glob import glob
from braceexpand import braceexpand
import numpy as np
import os
import argparse

"""
This script calculates the EETC statistics for wind and precipitation for each extreme storm that has affected Quebec by loading only 14 months of data.
It can be run in parallel for different years and simulations (see /JOBS/submit_EETCs_stat.sh script).
Once all years have been run for a simulation, it requires the append_pickle_EETCs_stat.py script to append the results of all years into a single pickle file per simulation.

Author: Dr. Victorien De Meyer
Created: January 2025
Last update: November 2025
"""

def braced_glob(path):
    """
    Expand braces in the given path and return a list of matching file paths.
    """
    l = []
    for x in braceexpand(path):
        l.extend(glob(x))          
    return l

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees).
    Works correctly with longitude formats -180/180 or 0/360.
    
    Used to calculate distance between storm center and grid points
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    
    # haversine formula
    dlon = lon2 - lon1
    # Normalize dlon to [-pi, pi] to handle antimeridian crossing
    dlon = np.arctan2(np.sin(dlon), np.cos(dlon))
    dlat = lat2 - lat1
    
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    km = 6367 * c
    return km


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
        # period = (
        #     '2063-2097' if sim == 'UBI' and future
        #     else '2066-2100' if future and sim in future_hist_sim
        #     else '1980-2014'
        # )
        period = (
            '2058-2082' if future and sim in future_hist_sim
            else '1980-2004'
        )
        filename = f"{prefix}_{base_sim.lower()}_percentile_{period}{wetdays_str}.nc"

    file_path = f"{base_dir}{base_sim}/{var_dir}/{filename}"

    print(f"\nLoading percentile file: {file_path}\n")

    percentile = xr.open_dataset(file_path)

    if original_selection and variable == 'pr' and sim != 'ERA5':
        percentile['pr'] = percentile.pr * 3600.  #original percentiles were not in mm/h

    return percentile


def main(iyear, sim, metric, wetdays, future, original_selection, output_file):

    future_hist_sim = {'UBG': 'UBD', 'UBH': 'UBE', 'UBI': 'UBF'}

    if sim in future_hist_sim:
        hist_sim = future_hist_sim[sim]

    # Define expected time range to check if time dimension of datasets is correct
    if sim != 'ERA5' and iyear == 1979:
        start = f"{iyear}-09-01 01:00:00"
        end = f"{iyear+1}-02-25 23:00:00"
    elif sim == 'ERA5' and iyear == 2023:
        start = f"{iyear}-01-01 00:00:00"
        end = f"{iyear}-08-31 23:00:00"
    elif (sim in ['UBD', 'UBE', 'UBF'] and iyear == 2014) or (sim == 'UBB' and iyear == 2023):
        start = f"{iyear}-01-01 00:00:00"
        end = f"{iyear}-12-31 23:00:00"
    elif sim in ['UBG', 'UBH'] and iyear == 2100:
        start = f"{iyear}-01-01 00:00:00"
        end = f"{iyear}-12-30 23:00:00"
    elif sim == 'UBI' and iyear == 2098:
        start = f"{iyear}-01-01 00:00:00"
        end = f"{iyear}-04-30 23:00:00"
    else:
        start = f"{iyear}-01-01 00:00:00"
        end = f"{iyear+1}-02-25 23:00:00"

    expected_time = pd.date_range(
        start=start,
        end=end,
        freq="h"
    ).to_numpy()


    # Load storm tracking data
    df = pd.read_csv(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/{sim}_psl_smooth_400km_12h_1005hPa.txt',
                    sep=r' ', header=0, engine='python', names=['storm','point','i','j','date','lat','lon','pressure'])
    df['date'] = pd.to_datetime(df['date'])



    #---------------------- PRECIPITATION ----------------------

    # Load precipitation data, 14 months to cover Jan 1 to Feb 25 of the next year, so that we can capture the whole storm event if it crosses the year boundary
    if sim == 'ERA5':
        input_dir = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/ERA5/PR'
        filenames_precip = sorted(glob(f'{input_dir}/{iyear}/*/*.nc4'))
        if iyear != 2023:
            filenames_precip += braced_glob(f'{input_dir}/{iyear+1}/{{01,02}}/*.nc4')
    else:
        if sim in future_hist_sim and iyear == 2014:
            filenames_precip = braced_glob(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{hist_sim}/PR/pr_{hist_sim.lower()}_{iyear}*_se.nc')
        else:
            filenames_precip = braced_glob(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/PR/pr_{sim.lower()}_{iyear}*_se.nc')
        f2 = f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/PR/pr_{sim.lower()}_{iyear+1}{{01,02}}_se.nc'
        filenames_precip.extend(braced_glob(f2))

    ds_precip = xr.open_mfdataset(
        filenames_precip,
        combine="by_coords",        
        data_vars="minimal",        # n'empile que les vraies variables de données
        coords="minimal",           # n'empile pas 36 fois la même grille
        compat="override",          # évite les conflits inutiles si les attrs diffèrent
    )

    if sim == 'ERA5':
        mask = xr.open_dataarray('/home/vdemeyer/projects/rrg-gachon/vdemeyer/MASK/mask_CRCM6_grid_for_ERA5.nc')
        ds_precip = ds_precip.assign_coords({'longitude': (((ds_precip['longitude'] + 180) % 360) - 180)})
        ds_precip = ds_precip.sortby(ds_precip['longitude'])
        ds_precip = ds_precip.where(mask, drop=True)
        ds_precip = ds_precip.rename({'tp': 'pr'})
        ds_precip['pr'] = ds_precip.pr * 1000.
    else:
        ds_precip['time'] = ds_precip['time'].dt.floor('h') #correct small inaccuracies in time (ex: '2012-01-01T01:29:59.999999872' becomes '2012-01-01T01:30:00.000000000')
        ds_precip['pr'] = ds_precip.pr * 3600. #convert from mm/s to mm/h
    
    ds_precip = ds_precip.sel(time=slice(f'{iyear}-01-01', f'{iyear+1}-02-25'))

    # Check if time dimension is correct
    if sim != 'ERA5':
        if iyear == 1979:
            expected_start_time = '1979-09-01 01:00:00'
            ds_precip = ds_precip.isel(time=slice(1, None))
        else:
            expected_start_time = f'{iyear}-01-01 00:00:00'
    
        actual_start_time_precip = ds_precip['time'][0].dt.strftime('%Y-%m-%d %H:%M:%S').values
        if actual_start_time_precip != expected_start_time:
            raise ValueError(f"The first time coordinate for precipitation is not {expected_start_time} but {actual_start_time_precip}")

    if not np.array_equal(ds_precip['time'].to_numpy(), expected_time):
        raise ValueError(f"The time coordinates for precipitation is wrong")

    # Load percentile data
    percentile_precip = selection_percentile(sim, future_hist_sim, variable='pr', wetdays=wetdays, future=future, original_selection=original_selection)

    # Calculate exceedance over percentile, set negative values to NaN. Positive values indicate exceedance. Metric can be 'diff' or 'ratio'.
    if metric == 'diff':
        mask_diff_precip = ds_precip - percentile_precip#.pr
    elif metric == 'ratio':
        mask_diff_precip = (ds_precip - percentile_precip) / percentile_precip 
    else:
        raise ValueError(f"Unknown metric: {metric}")
    
    mask_diff_precip = mask_diff_precip.where(mask_diff_precip >= 0., np.nan)

    if sim != 'ERA5':
        mask_diff_precip = mask_diff_precip.chunk({'rlat': 50, 'rlon': 50, 'time': 250, 'quantile': 4}) #Rechunk to optimize memory usage


    #---------------------- WIND ----------------------
    #Same procedure for wind data. See precipitation comments for explanations.

    if sim == 'ERA5':
        input_dir = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/ERA5/WIND/Magnitude'
        filenames_wind = sorted(glob(f'{input_dir}/{iyear}/*/*.nc4'))
        if iyear != 2023:
            filenames_wind += braced_glob(f'{input_dir}/{iyear+1}/{{01,02}}/*.nc4')
    else:
        if sim in future_hist_sim and iyear == 2014:
            filenames_wind = braced_glob(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{hist_sim}/WIND/wind10_{hist_sim.lower()}_{iyear}*_se.nc')
        else:
            filenames_wind = braced_glob(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/WIND/wind10_{sim.lower()}_{iyear}*_se.nc')
        f2 = f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/WIND/wind10_{sim.lower()}_{iyear+1}{{01,02}}_se.nc'
        filenames_wind.extend(braced_glob(f2))

    ds_wind = xr.open_mfdataset(
        filenames_wind,
        combine="by_coords",        
        data_vars="minimal",
        coords="minimal",
        compat="override",  
    )
    
    if sim == 'ERA5':
        ds_wind = ds_wind.assign_coords({'longitude': (((ds_wind['longitude'] + 180) % 360) - 180)})
        ds_wind = ds_wind.sortby(ds_wind['longitude'])
        ds_wind = ds_wind.where(mask, drop=True)
    else:
        ds_wind['time'] = ds_wind['time'].dt.round('h') #correct small inaccuracies in time (ex: '2012-01-01T01:59:59.999999872' becomes '2012-01-01T02:00:00.000000000'). Not the same as for precip because of different rounding issues.
    
    ds_wind['surf_wind'] = ds_wind.surf_wind * 3.6
    ds_wind = ds_wind.sel(time=slice(f'{iyear}-01-01', f'{iyear+1}-02-25'))
    if sim in future_hist_sim and iyear == 2100:
        ds_wind = ds_wind.isel(time=slice(0, -1)) #There is one hour of data on 2100-12-31T00:00:00.000000000 that does not exist in the precipitation file

    if sim != 'ERA5':
        actual_start_time_wind = ds_wind['time'][0].dt.strftime('%Y-%m-%d %H:%M:%S').values
        if actual_start_time_wind != expected_start_time:
            raise ValueError(f"The first time coordinate for wind is not {expected_start_time} but {actual_start_time_wind}")

    if not np.array_equal(ds_wind['time'].to_numpy(), expected_time):
        raise ValueError(f"The time coordinates for wind is wrong")
    
    percentile_wind = selection_percentile(sim, future_hist_sim, variable='ws', wetdays=wetdays, future=future, original_selection=original_selection)
            
    percentile_wind['surf_wind'] = percentile_wind.surf_wind * 3.6
    percentile_wind_for_SSI = percentile_wind.where(percentile_wind >= 9*3.6, 9*3.6) #for Storm Severity Index (SSI) calculation, we set the minimum value to 9 m/s (32.4 km/h) if the percentile is lower than that
            
    if metric == 'diff':
        mask_diff_wind = ds_wind - percentile_wind 
    elif metric == 'ratio':
        mask_diff_wind = (ds_wind - percentile_wind) / percentile_wind 

    mask_diff_wind = mask_diff_wind.where(mask_diff_wind >= 0., np.nan)
    mask_diff_wind_SSI = ds_wind / percentile_wind_for_SSI #For SSI calculation

    if sim != 'ERA5':
        mask_diff_wind = mask_diff_wind.chunk({'rlat': 50, 'rlon': 50, 'time': 250, 'quantile': 4})
        mask_diff_wind_SSI = mask_diff_wind_SSI.chunk({'rlat': 50, 'rlon': 50, 'time': 250, 'quantile': 4})




    #---------------------- EETC CALCULATION ----------------------

    #Coordinates of the region (South Quebec) over which we calculate the EETC statistics
    west_lon = -80
    east_lon = -66
    north_lat = 55
    south_lat = 44

    #Selection of the region in the datasets
    if sim == 'ERA5':
        mask_diff_wind_quebec = mask_diff_wind.sel({'longitude': slice(west_lon, east_lon), 'latitude': slice(north_lat, south_lat)}).compute()
        mask_diff_wind_SSI_quebec = mask_diff_wind_SSI.sel({'longitude': slice(west_lon, east_lon), 'latitude': slice(north_lat, south_lat)}).compute()
        mask_diff_precip_quebec = mask_diff_precip.sel({'longitude': slice(west_lon, east_lon), 'latitude': slice(north_lat, south_lat)}).compute()

        Quebec_nb_gridbox = mask_diff_wind_quebec.isel(time=0, quantile=0).sizes['longitude'] * mask_diff_wind_quebec.isel(time=0, quantile=0).sizes['latitude']

    else:
        mask = (
            (percentile_precip.lon >= west_lon) &
            (percentile_precip.lon <= east_lon) &
            (percentile_precip.lat >= south_lat) &
            (percentile_precip.lat <= north_lat)
        )

        mask_diff_wind_quebec = mask_diff_wind.where(mask, drop=True).compute()
        mask_diff_wind_SSI_quebec = mask_diff_wind_SSI.where(mask, drop=True).compute()
        mask_diff_precip_quebec = mask_diff_precip.where(mask, drop=True).compute()

        Quebec_nb_gridbox = mask_diff_wind_quebec.isel(time=0, quantile=0).sizes['rlon'] * mask_diff_wind_quebec.isel(time=0, quantile=0).sizes['rlat']

    # Get unique storm indices for the given year
    storm_indices_iyear = [id_storm for id_storm, group in df.groupby('storm') if group.iloc[0]['date'].year == iyear]
    # storm_indices_iyear = df[df['date'].dt.year == iyear]['storm'].unique()
    print(f"Number of storms in {iyear}: {len(storm_indices_iyear)}")

    coord_lon = 'longitude' if sim == 'ERA5' else 'lon'
    coord_lat = 'latitude' if sim == 'ERA5' else 'lat'
    coord_lon2 = 'longitude' if sim == 'ERA5' else 'rlon'
    coord_lat2 = 'latitude' if sim == 'ERA5' else 'rlat'
    drop_boolean = False if metric == 'ratio' else True #important to keep all values across the quebec domain for the ratio metric because we add +1 to all grid points of iEETC_precip/wind_exc in the calculation of the metric
    
    EETC_dict = {}
    # Loop over each storm in the year
    for id_storm in storm_indices_iyear:
        group = df[df['storm'] == id_storm]

        iEETC_list_precip = []
        iEETC_list_wind = []
        iEETC_list_wind_SSI = []        
        iEETC_list_compound_quantile = []        

        for itrack, row in group.iterrows():        
            ilon, ilat, itime = row['lon'], row['lat'], row['date']

            #select the 1000km radius around the storm position at itime to get the exceedance values only in that area
            mask_itime_precip = mask_diff_precip_quebec.sel(time=itime).where(mask_diff_precip_quebec.sel(time=itime).map(lambda x: haversine(ilon, ilat, getattr(x, coord_lon), getattr(x, coord_lat)) <= 1000), drop=drop_boolean).pr
            mask_itime_wind   = mask_diff_wind_quebec.sel(time=itime).where(mask_diff_wind_quebec.sel(time=itime).map(lambda x: haversine(ilon, ilat, getattr(x, coord_lon), getattr(x, coord_lat)) <= 1000), drop=drop_boolean).surf_wind #value at itime
            
            #for SSI calculation, we take the max wind within +/-12h of itime, as Ting-Chen et al. (2025) did
            time_slice = slice(itime - pd.Timedelta(hours=12), itime + pd.Timedelta(hours=12))
            mask_itime_wind_SSI = mask_diff_wind_SSI_quebec.sel(time=time_slice).where(mask_diff_wind_SSI_quebec.sel(time=time_slice).map(lambda x: haversine(ilon, ilat, getattr(x, coord_lon), getattr(x, coord_lat)) <= 1000), drop=True).surf_wind.max(dim='time').expand_dims(time=[itime]) #max within +/-12h of itime for SSI calculation

            #for compound, we check within +/-8h of itime
            time_slice_compound = slice(itime - pd.Timedelta(hours=8), itime + pd.Timedelta(hours=8))
            mask_wind_cum_8hr = mask_diff_wind_quebec.sel(time=time_slice_compound).where(mask_diff_wind_quebec.sel(time=time_slice_compound).map(lambda x: haversine(ilon, ilat, getattr(x, coord_lon), getattr(x, coord_lat)) <= 1000), drop=True).surf_wind.sum(dim='time') 
            compound_quantile_8hrs = (mask_itime_precip > 0) & (mask_wind_cum_8hr > 0) #Si dans les 8 heures d'une précip > quantile il y'a des coordonnées lat/lon pour lesquels le vent était > quantile ça retourne True
                                    
            iEETC_list_precip.append(mask_itime_precip)
            iEETC_list_wind.append(mask_itime_wind)
            iEETC_list_wind_SSI.append(mask_itime_wind_SSI)            
            iEETC_list_compound_quantile.append(compound_quantile_8hrs)            

        #on concatène tous les cercles de 1000km de chaque pas de temps en un seul dataarray. On a donc un dataarray de tous les pas de temps de la tempête avec les valeurs d'excédent dans les 1000km autour de la tempête
        iEETC_precip = xr.concat(iEETC_list_precip, dim='time', join="outer", coords="different", compat="equals")  #join="outer" va prendre tous les indices possibles de latitude et longitude présents dans tous les fichiers
        iEETC_wind = xr.concat(iEETC_list_wind, dim='time', join="outer", coords="different", compat="equals") 
        iEETC_wind_SSI = xr.concat(iEETC_list_wind_SSI, dim='time', join="outer", coords="different", compat="equals")         
        iEETC_compound_quantile = xr.concat(iEETC_list_compound_quantile, dim='time', join="outer", coords="different", compat="equals")

        #on somme la précipitation excédente en chaque point de grille sur la durée de vie de l'ETC dans ses 1000km (2D)
        iEETC_precip_exc = iEETC_precip.sum(dim=['time']) 
        iEETC_wind_exc = iEETC_wind.sum(dim=['time'])        

        #on test voir si la tempête a affecté le Québec via le total d'excédent de précipitation et de vent sur le domaine (1D)
        if metric == 'ratio': 
            iEETC_precip_exc = iEETC_precip_exc + 1 #On rajoute 1 partout pour avoir le ratio variable/seuil avec des 1 partout ailleurs, qui permet d'avoir la métrique moyenne sur le domaine supérieure à 1
            iEETC_wind_exc   = iEETC_wind_exc   + 1
        test_quebec_affecte_precip = iEETC_precip_exc.sum(dim=[coord_lon2, coord_lat2])
        test_quebec_affecte_vent = iEETC_wind_exc.sum(dim=[coord_lon2, coord_lat2])

        #si la tempête a affecté le Québec, alors on calcule les métriques d'EETC
        if (
            (metric == 'ratio' and ((test_quebec_affecte_precip > Quebec_nb_gridbox).any() or (test_quebec_affecte_vent > Quebec_nb_gridbox).any())) or #Quebec_nb_gridbox because we added 1 to all grid points in the quebec domain
            (metric != 'ratio' and ((test_quebec_affecte_precip > 0).any() or (test_quebec_affecte_vent > 0).any()))
        ):

            #to compute the SSI for the wind
            iEETC_wind_SSI_max = iEETC_wind_SSI.max(dim=['time']) #we take the max of the wind within 1000km of the stormtrack
            SSI_map = (iEETC_wind_SSI_max - 1)**3 #we compute the SSI for the wind
            SSI = SSI_map.where(SSI_map > 0).sum(dim=(coord_lon2, coord_lat2)) / Quebec_nb_gridbox
            
            #on calcule le nombre de pas de temps avec une précipitation excédente sur chaque point de grille
            iEETC_precip_dur = iEETC_precip.where(iEETC_precip > 0).count(dim='time') 
            iEETC_wind_dur = iEETC_wind.where(iEETC_wind > 0).count(dim='time')
            
            #on calcule la précipitation excédente moyenne par heure avec une précipitation excédente
            iEETC_precip_avexc = (iEETC_precip_exc / iEETC_precip_dur).where(iEETC_precip_dur != 0)
            iEETC_wind_avexc = (iEETC_wind_exc / iEETC_wind_dur).where(iEETC_wind_dur != 0)

            #on calcule le nombre de points de grille affecté par une précipitation excédente dans les 1000km de l'ETC
            # iEETC_precip_nb_gridbox = iEETC_precip_exc.where(iEETC_precip_exc > 0).count(dim=['lon','lat']) 
            # iEETC_wind_nb_gridbox = iEETC_wind_exc.where(iEETC_wind_exc > 0).count(dim=['lon','lat'])

            #on calcule la précipitation excédente moyenne par point de grille de la région quebec
            iEETC_precip_exc_tot = test_quebec_affecte_precip / Quebec_nb_gridbox 
            iEETC_wind_exc_tot = test_quebec_affecte_vent / Quebec_nb_gridbox
            
            #on calcule la précipitation excédente moyenne par heure moyenne par point de grille de la région quebec
            if metric == 'ratio': 
                iEETC_precip_avexc = iEETC_precip_avexc.fillna(0) + 1 #On rajoute 1 partout pour avoir le ratio variable/seuil avec des 1 partout ailleurs, qui permet d'avoir la métrique moyenne sur le domaine supérieure à 1
                iEETC_wind_avexc = iEETC_wind_avexc.fillna(0) + 1
            iEETC_precip_avexc_tot = iEETC_precip_avexc.sum(dim=[coord_lon2, coord_lat2]) / Quebec_nb_gridbox 
            iEETC_wind_avexc_tot = iEETC_wind_avexc.sum(dim=[coord_lon2, coord_lat2]) / Quebec_nb_gridbox

            #on regarde si la tempête a amené un compound vent/précip extrême
            iEETC_compound_quantile = iEETC_compound_quantile.compute()
            compound_quantile = {
                '98': iEETC_compound_quantile.sel(quantile=0.98).any().item(),
                '99': iEETC_compound_quantile.sel(quantile=0.99).any().item(),
                '99.5': iEETC_compound_quantile.sel(quantile=0.995).any().item(),
                '99.9': iEETC_compound_quantile.sel(quantile=0.999).any().item()
            }
                        
        else: #si la tempête n'a pas affecté le Québec on met des valeurs nulles
            if metric == 'ratio':
                null_value = 1
            else:
                null_value = 0
            iEETC_precip_exc_tot = xr.DataArray(null_value, coords=test_quebec_affecte_precip.coords, dims=test_quebec_affecte_precip.dims)
            iEETC_precip_avexc_tot = xr.DataArray(null_value, coords=test_quebec_affecte_precip.coords, dims=test_quebec_affecte_precip.dims)
            iEETC_wind_exc_tot = xr.DataArray(null_value, coords=test_quebec_affecte_vent.coords, dims=test_quebec_affecte_vent.dims)
            iEETC_wind_avexc_tot = xr.DataArray(null_value, coords=test_quebec_affecte_vent.coords, dims=test_quebec_affecte_vent.dims)
            SSI = xr.DataArray(0, coords=test_quebec_affecte_vent.coords, dims=test_quebec_affecte_vent.dims)
            compound_quantile = {
                '98': False,
                '99': False,
                '99.5': False,
                '99.9': False
            }            

        EETC_dict[id_storm] = {
            'cum_precip': iEETC_precip_exc_tot,
            'cum_avg_precip': iEETC_precip_avexc_tot,
            'cum_wind': iEETC_wind_exc_tot,
            'cum_avg_wind': iEETC_wind_avexc_tot,
            'SSI': SSI,
            'compound_8hrs_quantile': compound_quantile,            
        }

    # Save the EETC statistics dictionary as a pickle file
    with open(output_file, "wb") as pickle_file:
        pickle.dump(EETC_dict, pickle_file)
    print(f'Pickle file written for year {iyear} in {output_file}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Calculate EETC statistics for wind and precipitation.')
    parser.add_argument('iyear', type=int, help='The year for which to calculate the statistics')
    parser.add_argument('--sim', type=str, required=True, help='Name of the simulation')
    parser.add_argument('--metric', type=str, required=True, help='ratio or diff for the extreme metric calculation')
    parser.add_argument('--wetdays', action='store_true', help='Computation done with percentile calculated on wet days only for precipitation')
    parser.add_argument('--future', action='store_true', help='Computation done with percentile calculated on future period for future simulations')
    parser.add_argument('--original_selection', action='store_true', help='Use original selection criteria, with percentiles calculated on the full historical period')

    args = parser.parse_args()

    iyear = args.iyear
    sim = args.sim
    metric = args.metric
    wetdays = args.wetdays
    future = args.future
    original_selection = args.original_selection

    output_dir = f"/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/EETC/{sim}/{iyear}"
    os.makedirs(output_dir, exist_ok=True)

    
    output_file = f'{output_dir}/EETC_cum_{sim}_Quebec_1005hPa_{iyear}_compound_8hrs_quantile_SSI'

    if original_selection and (wetdays or future or metric=='ratio'):
        raise ValueError("original_selection cannot be combined with wetdays, future or ratio metric")
    if not original_selection:
        if wetdays:
            output_file += '_wetdays'
        if future and sim in ['UBG', 'UBH', 'UBI']:
            output_file += '_future_percentile'
        output_file += f'_{metric}.pkl'

    if os.path.exists(output_file):
        os.remove(output_file)

    main(iyear, sim, metric, wetdays, future, original_selection, output_file)

# run /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/EETCs_stat.py 2023 --sim UBB --metric diff --future
