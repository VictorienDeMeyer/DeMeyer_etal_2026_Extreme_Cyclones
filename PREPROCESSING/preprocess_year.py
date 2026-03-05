import xarray as xr
from glob import glob
import numpy as np
import dask_image.ndfilters as dfilters
import dask.array as da
from braceexpand import braceexpand
import os
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import argparse
import cftime
import pandas as pd

"""
Script to preprocess the dataset in order to track ETCs with Katja's algorithm.
It may needs some minor adjustements to make sure it runs smoothly for different dataset, especially haversine with an irregular grid.
It convert the grid (convert_lon_lat), select the domain (get_mask), make sure the variable has the right unit (get_sea_level_pressure), smooth the field (smooth_uniform) and convert the calendar if needed (calendar_conversion).

Last update: January 2026
"""
    
def calc_grid_distance_area(longitude, latitude):
    """ Function to calculate grid parameters
        It uses haversine function to approximate distances
        It approximates the first row and column to the sencond
        because coordinates of grid cell center are assumed
        lat, lon: input coordinates(degrees) 2D [y,x] dimensions
        dx: distance (m)
        dy: distance (m)
        grid_distance: average grid distance over the domain (m)
    """

    if longitude.ndim < 2:
        lon, lat = np.meshgrid(longitude, latitude)
    else:
        lon, lat = longitude.values, latitude.values
    
    dy = np.zeros(lon.shape)
    dx = np.zeros(lat.shape)

    dx[:,1:]=haversine(lon[:,1:],lat[:,1:],lon[:,:-1],lat[:,:-1])
    dy[1:,:]=haversine(lon[1:,:],lat[1:,:],lon[:-1,:],lat[:-1,:])

    dx[:,0] = dx[:,1]
    dy[0,:] = dy[1,:]
    
    dx = dx * 10**3
    dy = dy * 10**3

    grid_distance = np.mean(np.append(dy[:, :, None], dx[:, :, None], axis=2))

    return grid_distance

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
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

def get_sim_context(sim, year, base_dir='/home/vdemeyer/projects/rrg-gachon/vdemeyer'):
    """
    Handles paths, dates, and precise file selection logic.
    Optimized for nested directory structures and 2083 transition.
    """
    sim_lower = sim.lower()
    
    # 1. Default Strategy: Dec (Y-1) + All Y + Jan (Y+1)
    file_strategy = [(year - 1, 12), (year, 'all'), (year + 1, 1)]

    start = f"{year-1}-12-01 00:00:00"
    end = f"{year+1}-01-31 23:00:00"

    # 2. Refined Exceptions Handling for Dates and Strategy
    if sim == 'ERA5':
        if year == 1979:
            file_strategy = [(year, 'all'), (year + 1, 1)]
            start = f"{year}-01-01 00:00:00"
        elif year == 2023:
            file_strategy = [(year - 1, 12), (year, 'all')]
            end = f"{year}-08-31 23:00:00"

    elif sim == 'UBB':
        if year == 1979:
            file_strategy = [(year, 'all'), (year + 1, 1)]
            start = f"{year}-09-01 01:00:00"
        elif year == 2023:
            file_strategy = [(year - 1, 12), (year, 'all')]
            end = f"{year}-12-31 23:00:00"

    elif sim in ['UBD', 'UBE', 'UBF']:
        if year == 1979:
            file_strategy = [(year, 'all'), (year + 1, 1)]
            start = f"{year}-09-01 01:00:00"
        elif year == 2014:
            file_strategy = [(year - 1, 12), (year, 'all')]
            end = f"{year}-12-31 23:00:00"

    elif sim in ['UBG', 'UBH', 'UBI']:
        if year == 2015:
            file_strategy = [(year, 'all'), (year + 1, 1)]
            start = f"{year}-01-01 01:00:00"
        if year == 2100 and sim in ['UBG', 'UBH']:
            file_strategy = [(year - 1, 12), (year, 'all')]
            end = f"{year}-12-31 00:00:00"
        elif year == 2098 and sim == 'UBI':
            file_strategy = [(year - 1, 12), (year, 'all')]
            end = f"{year}-04-30 23:00:00"

    # 3. Dynamic File List Building
    input_files = []
    
    for y, m in file_strategy:
        
        t_dir = f"{base_dir}/{sim}/PSL"
        if sim == 'ERA5':
            pattern = f"{t_dir}/{y}/*/*.nc4" if m == 'all' else f"{t_dir}/{y}/{m:02d}/*.nc4"
        else:
            pattern = f"{t_dir}/psl_{sim_lower}_{y}*_se.nc" if m == 'all' else f"{t_dir}/psl_{sim_lower}_{y}{m:02d}_se.nc"
        found_files = sorted(glob(pattern))
    
        input_files.extend(found_files)

    return input_files, start, end

def convert_lon_lat(ds, var_lon, var_lat, to_180=True):
    """
    Convertit les coordonnées lon/lat sur une grille -180:180 ou 0:360.
    
    Args:
        ds (xarray.Dataset): Dataset d'entrée.
        var_lon (str): Nom de la dimension/variable longitude.
        var_lat (str): Nom de la dimension/variable latitude.
        to_180 (bool): Si True, convertit vers -180:180. 
                       Si False, convertit vers 0:360.
    """
    
    if ds[var_lon].ndim == 2:
        print('\nLongitude and Latitude are 2D arrays')
        
        if to_180:
            # Conversion vers -180:180
            if (ds[var_lon] >= 180.).any():
                ds[var_lon] = (((ds[var_lon] + 180) % 360) - 180)
                print('Longitude converted to -180:180 grid')
        else:
            # Conversion vers 0:360
            if (ds[var_lon] < 0.).any():
                ds[var_lon] = (ds[var_lon] % 360)
                print('Longitude converted to 0:360 grid')

        # La latitude reste généralement en -90:90, on garde ta logique de sécurité
        if (ds[var_lat] > 90.).any() or (ds[var_lat] < -90.).any():
            ds[var_lat] = (((ds[var_lat] + 90) % 180) - 90)
            print('Latitude converted to -90:90 grid')

    else:
        # Cas des coordonnées 1D
        if to_180:
            if any(ds[var_lon] >= 180.):
                ds = ds.assign_coords({var_lon: (((ds[var_lon] + 180) % 360) - 180)})
                print('Longitude converted to -180:180 grid')
        else:
            if any(ds[var_lon] < 0.):
                ds = ds.assign_coords({var_lon: (ds[var_lon] % 360)})
                print('Longitude converted to 0:360 grid')

        if any(ds[var_lat] > 90.) or any(ds[var_lat] < -90.):
            ds = ds.assign_coords({var_lat: (((ds[var_lat] + 90) % 180) - 90)})
            print('Latitude converted to -90:90 grid')

        # Réorganisation de la grille (important après conversion)
        ds = ds.sortby(ds[var_lon])

    # --- Vérifications (Assertions) adaptées ---
    if to_180:
        assert ds[var_lon].min() >= -180.0, 'Min longitude < -180'
        assert ds[var_lon].max() <= 180.0, 'Max longitude > 180'
    else:
        assert ds[var_lon].min() >= 0.0, 'Min longitude < 0'
        assert ds[var_lon].max() <= 360.0, 'Max longitude > 360'
        
    assert ds[var_lat].min() >= -90.0, 'Min latitude < -90'
    assert ds[var_lat].max() <= 90.0, 'Max latitude > 90'

    return ds

def get_mask(ds, var_lon, var_lat, west_longitude=-180, east_longitude=180, north_latitude=90, south_latitude=-90, plot=False):
    
    if ds[var_lon].ndim == 2:
        mask = (
                (ds[var_lon] >= west_longitude) &
                (ds[var_lon] <= east_longitude) &
                (ds[var_lat] >= south_latitude) &
                (ds[var_lat] <= north_latitude)
            )
        ds = ds.where(mask, drop=True)
        # ds = masked_ds.dropna(dim='rlon', how='all').dropna(dim='rlat', how='all') #pas nécessaire visiblement
        
    else:
        ds = ds.sel({var_lon: slice(west_longitude, east_longitude), var_lat: slice(north_latitude, south_latitude)})
    
    if plot==True:
        if ds[var_lon].ndim == 2:
            Mask = np.copy(ds[var_lon]); Mask[:]=1
            pole_lon = ds.rotated_pole.attrs['grid_north_pole_longitude']
            pole_lat = ds.rotated_pole.attrs['grid_north_pole_latitude']
            plotcrs = ccrs.RotatedPole(pole_longitude=pole_lon, pole_latitude=pole_lat)
            lon = ds.rlon
            lat = ds.rlat
        else:
            Mask = np.ones((len(ds[var_lat]), len(ds[var_lon])))
            plotcrs = ccrs.PlateCarree()
            lon = ds[var_lon]
            lat = ds[var_lat]
        fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(projection=ccrs.PlateCarree()))
        ax.set_extent([-180, 180, -90, 90], crs=ccrs.PlateCarree())
        ax.coastlines()
        plt.pcolormesh(
            lon,
            lat,
            Mask,
            transform=plotcrs,
            cmap="coolwarm",
            alpha=0.5,
        )
        plt.title('Region where storm tracking is performed')
        plt.show()
        
    return ds

def get_sea_level_pressure(ds):
    if hasattr(ds, 'msl'):
        slp = ds.msl
    elif hasattr(ds, 'psl'):
        slp = ds.psl
    elif hasattr(ds, 'SLP'):
        slp = ds.SLP
    elif hasattr(ds, 'slp'):
        slp = ds.slp
    else:
        raise AttributeError(f'No variables psl, SLP, slp or msl in {input_files[0].split("/")[-1]}')

    try:
        slp_units = slp.attrs['units']
    except KeyError:
        raise KeyError(f'Mean sea level pressure variable in {input_files[0].split("/")[-1]} must have a units attribute')

    if slp_units == 'hPa':
        slp = slp / 100.
        slp.attrs['units'] = 'Pa'
    elif slp_units != 'Pa':
        raise ValueError("Mean sea level pressure units are not Pa or hPa")

    print('\nSlp unit: ', slp.attrs['units'])
    
    # assert slp.min() >= 90000., 'There is at least one mean sea level pressure less than 900hPa'
    # assert slp.max() < 110000., 'There is a mean sea level pressure value > 1100hPa'
    
    return slp

def smooth_uniform(data, t_smoot, xy_smooth):
    """
    Spatiotemporal uniform smoothing of atmospheric fields,
    robust to missing values (NaN-aware).
    
    Parameters
    ----------
    data : xr.DataArray
        Input field with dimensions (time, lat, lon)
    t_smoot : int
        Temporal window length (time steps)
    xy_smooth : int
        Spatial window length (grid points)
    """

    # 1. Masque de données valides
    valid = xr.where(data.isnull(), 0.0, 1.0)

    # 2. Remplacer les NaN par 0 pour que la somme (num) ne soit pas NaN
    data_filled = data.fillna(0.0)

    # 3. Appliquer le filtre uniform
    num = dfilters.uniform_filter(data_filled.data, 
                                  size=[int(t_smoot), int(xy_smooth), int(xy_smooth)])
    
    den = dfilters.uniform_filter(valid.data, 
                                  size=[int(t_smoot), int(xy_smooth), int(xy_smooth)])

    # 4. Calculer la moyenne uniquement là où den > 0 pour éviter le warning
    # On utilise np.where sur les arrays dask/numpy sous-jacents
    with np.errstate(divide='ignore', invalid='ignore'):
        smooth_data = da.where(den > 0, num / den, np.nan)

    # 5. Reconstruire le DataArray
    smooth = xr.DataArray(smooth_data, coords=data.coords, dims=data.dims, name='slp')

    print('\nSmoothing applied with temporal window of', t_smoot, 'time steps and spatial window of', xy_smooth, 'grid points')

    # IMPORTANT : Ré-appliquer le masque initial pour garantir le domaine strict
    return smooth.where(valid == 1).rename('slp')

def calendar_conversion(ds):

    current_calendar = ds.time.encoding.get("calendar", "No calendar attribute")

    if current_calendar != "proleptic_gregorian":
        ds = ds.convert_calendar("proleptic_gregorian", dim="time", use_cftime=True)
        print(f"\nCalendar converted to {ds.time.encoding.get('calendar', 'proleptic_gregorian')}\n")
    else:
        print(f"\nCalendar is already {current_calendar}\n")

    new_units = "hours since 1970-01-01 00:00:00"
    new_calendar = "proleptic_gregorian"
    
    time_hours = cftime.date2num(ds["time"].values, new_units, new_calendar)

    ds = ds.assign_coords(time=("time", time_hours))

    ds["time"].attrs["units"] = new_units
    ds["time"].attrs["calendar"] = new_calendar
    ds["time"].encoding.update({
        "units": new_units,
        "calendar": new_calendar,
        "dtype": np.float64
    })

    return ds
    
def main(year, sim):
    """
    This function includes the main program. It makes sure the input file provided 
    has the necessary variables to track extratropical cyclones, the variables have the
    right units and the grid is the correct one. It then runs smoothing over the preprocessed
    input file. No smoothing is performed over the time dimension so the smoothing can be 
    done file by file.
    """

    input_files, start, end = get_sim_context(sim, year)

    output_dir = f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/INPUTS/{sim}'
    os.makedirs(output_dir, exist_ok=True)

    output_file = f'{output_dir}/{sim}_psl_smoothed_400km_{year}_pres.nc'
    if os.path.exists(output_file):
        os.remove(output_file)
        print(f'\nOld {year} single NetCDF file removed')
        # print(f'\n{year} single NetCDF file already exists')
        # continue

    if not input_files:
        print(f"\nNo input files found for {year}, stopping program.")
        return
    print(f'\nFirst input file for {year}:', input_files[0].split("/")[-1])

    expected_time = pd.date_range(start=start, end=end, freq="h").to_numpy()

    ds = xr.open_mfdataset(input_files, combine='by_coords')

    if hasattr(ds, 'lon'):
        var_lon, var_lat = 'lon', 'lat'
    elif hasattr(ds, 'longitude'):
        var_lon, var_lat = 'longitude', 'latitude'
    else:
        raise AttributeError(f'No dimension lon or longitude / lat or latitude in {input_files[0].split("/")[-1]}')
      
    if sim=='ERA5':
        ds = convert_lon_lat(ds, var_lon, var_lat, to_180=False)
        mask = xr.open_dataarray('/home/vdemeyer/projects/rrg-gachon/vdemeyer/MASK/mask_CRCM6_grid_for_ERA5_0_360.nc')
        ds = ds.where(mask, drop=True)
        # ds = get_mask(ds, var_lon, var_lat, west_longitude=-171+360, east_longitude=-23+360, north_latitude=76, south_latitude=12, plot=False)
    else:
        ds['time'] = ds['time'].dt.round('h')
    
    if not np.array_equal(ds['time'].to_numpy(), expected_time):
        raise ValueError(f"The time coordinates is wrong")

    slp = get_sea_level_pressure(ds)

    Gridspacing = calc_grid_distance_area(slp[var_lon], slp[var_lat])

    slp = smooth_uniform(slp, int(1), int(int(400/(Gridspacing/1000)))) #int(78/dT) - 3 jours / tous les 400km en moyenne ce qui correspond int(int(400/(Gridspacing/1000))) pts de grille
    slp = slp.assign_attrs(units='Pa', long_name='Mean sea level pressure', standard_name='air_pressure_at_mean_sea_level')
    slp = calendar_conversion(slp)

    if sim == 'ERA5':
        slp = slp.reindex(latitude=mask.latitude, longitude=mask.longitude)

    print('\n#####################################################################\n', slp,'\n\n#####################################################################')
    
    slp.to_netcdf(output_file)

    print(f'\n{year} NetCDF file created succesfully')
    
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Name of the simulation whose slp is to be smoothed')
    parser.add_argument('year', type=int, help='The year for which to smooth the sea level pressure')
    parser.add_argument('--sim', type=str, required=True, help='Name of the simulation')
    args = parser.parse_args()
    sim = args.sim
    year = args.year

    main(year, sim)

    # run /home/vdemeyer/TRACKING/KATJA/PREPROCESSING/preprocess_year.py 2012 --sim UBF 
    # . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_preprocess_year.sh