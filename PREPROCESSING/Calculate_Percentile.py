import xarray as xr
from glob import glob
from braceexpand import braceexpand
import argparse
import os

"""
This script calculates percentiles for specified variables (Precipitation or Wind) from different simulations (e.g., UBB, UBF) or ERA5.
To calculate the conditional precipitation percentile (only wet days), use the --cond flag.
FYI, ERA5 precipitation is in m/h, while CRCM6 sim are in kg/m²/s. The returned percentiles are all in mm/h.
All wind variables are in m/s.
"""

def braced_glob(path):
    l = []
    for x in braceexpand(path):
        l.extend(glob(x))          
    return l

def calculate_percentile(output_file, ds_variable, filenames, sim, start_year, end_year):

    if args.cond:
        log_file = f'/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/Percentile_{ds_variable}_{sim.lower()}_wetdays.txt'
    else:
        log_file = f'/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/Percentile_{ds_variable}_{sim.lower()}.txt'
    
    if os.path.exists(log_file):
        os.remove(log_file)

    def log_print(*args, **kwargs):
        with open(log_file, 'a') as f:
            print(*args, **kwargs, file=f)

    try:
        is_era5 = sim == 'ERA5'
        mask = xr.open_dataarray('/home/vdemeyer/projects/rrg-gachon/vdemeyer/MASK/mask_CRCM6_grid_for_ERA5.nc') if is_era5 else None
        
        dim_spec = ("latitude", "longitude") if is_era5 else ("rlat", "rlon")
        chunks = {dim: 128 for dim in dim_spec}
        chunks["time"] = 720
        
        ds = xr.open_mfdataset(
            filenames,
            combine="nested",
            concat_dim="time",
            chunks=chunks,
            data_vars="minimal",
            coords="minimal",
            compat="override",
            parallel=True
        )
        ds = ds.sel(time=slice(f'{start_year}-01-01', f'{end_year}-12-31')).chunk(chunks)

        if sim != 'ERA5':
            if variable == 'PR':
                ds[ds_variable] = ds[ds_variable] * 3600  # Convertir en mm/h
                ds['time'] = ds['time'].dt.floor('h')
            elif variable == 'WIND':
                ds['time'] = ds['time'].dt.round('h')
        else:
            if variable == 'PR':
                ds[ds_variable] = ds[ds_variable] * 1000  # Convertir en mm/h
            ds = ds.assign_coords({'longitude': (((ds['longitude'] + 180) % 360) - 180)})
            ds = ds.sortby(ds['longitude'])
            mask = mask.assign_coords({'longitude': (((mask['longitude'] + 180) % 360) - 180)})
            mask = mask.sortby(mask['longitude'])
            ds = ds.where(mask, drop=True)

        log_print(ds, '\n\n\n')

        if args.cond and variable == 'PR':
            percentiles = ds[ds_variable].where((ds[ds_variable] > 0.1).compute(), drop=True).quantile([0.98, 0.99, 0.995, 0.999], method='lower', dim='time', skipna=True) #conditionnel
        else:
            skipna_value = True if sim == 'UBB' else False
            percentiles = ds[ds_variable].quantile([0.98, 0.99, 0.995, 0.999], method='lower', dim='time', skipna=skipna_value)
        
        if sim != 'ERA5':
            for_pole = xr.open_dataset('/home/vdemeyer/projects/rrg-gachon/vdemeyer/UBB/PR/pr_ubb_202001_se.nc')
            percentiles["rotated_pole"] = for_pole["rotated_pole"]
            attrs_to_copy = [
                "grid_mapping_name",
                "grid_north_pole_latitude",
                "grid_north_pole_longitude",
                "north_pole_grid_longitude"
            ]
            for attr in attrs_to_copy:
                if attr in for_pole.attrs:
                    percentiles.attrs[attr] = for_pole.attrs[attr]

        
        units_map = {'PR': 'mm/h', 'WIND': 'm/s'}
        if variable in units_map:
            percentiles.attrs['units'] = units_map[variable]

        if sim == 'ERA5' and variable == 'PR':
            # percentiles = percentiles.rename({ds_variable: 'pr'})
            percentiles = percentiles.rename('pr')
            
        log_print(percentiles, '\n\n\n')

        try:
            percentiles.to_netcdf(output_file)
            log_print(f"Percentile file created at {output_file}")
        
        except Exception as e:
            log_print(f"Error writing file: {e}")
    
    except Exception as e:
        log_print(f"Error in calculate_percentile: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate percentiles for a given variable.")
    parser.add_argument('--variable', type=str, required=True, help='Variable to process (e.g., Precipitation, Wind)')
    parser.add_argument('--sim', type=str, required=True, help='Name of the simulation')
    parser.add_argument('--cond', action='store_true', help='Compute the conditional precipitation percentile (optional)')

    args = parser.parse_args()
    
    sim = args.sim
    if args.variable == 'Precipitation':
        ds_variable = 'pr'
        name_for_file = ds_variable
        variable = 'PR'
    elif args.variable == 'Wind':
        ds_variable = 'surf_wind'
        variable = 'WIND'
        name_for_file = 'wind10'
    else:
        raise ValueError(f"Variable {args.variable} not recognized.")

    if sim == 'ERA5':
        if variable == 'PR':
            # filenames = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/ERA5/PR/era5_tp_CORDEX_NA_1979-2023.zarr'
            filenames =  sorted(braced_glob('/home/vdemeyer/projects/rrg-gachon/vdemeyer/ERA5/PR/*/*/era5_tp_ll_*_1h.nc4'))
            ds_variable = 'tp'
        elif variable == 'WIND':
            # filenames = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/ERA5/WIND/Magnitude/era5_wind10_CORDEX_NA_1979-2023.zarr'
            filenames =  sorted(braced_glob('/home/vdemeyer/projects/rrg-gachon/vdemeyer/ERA5/WIND/Magnitude/*/*/era5_wind10_ll_*_1h.nc4'))
        else:
            raise ValueError(f"Variable {variable} not recognized for ERA5.")
    else:
        filenames = sorted(braced_glob(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{variable}/{name_for_file}_{sim.lower()}_*_se.nc'))

    if sim == 'ERA5' and args.variable == 'Precipitation':
        name_for_output_file = 'pr'
    else:
        name_for_output_file = ds_variable

    if not filenames:
        raise FileNotFoundError(f"No files found for variable {variable} for {sim}")
    
    output_dir = f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{variable}_Percentile'
    os.makedirs(output_dir, exist_ok=True)
    
    sim_hist_fut = {'UBD': 'UBG', 'UBE': 'UBH', 'UBF': 'UBI'}

    if sim in sim_hist_fut or sim in ['ERA5', 'UBB']:
        start_year, end_year = 1980, 2014
        # start_year, end_year = 1980, 2004
    else:
        # start_year, end_year = 2058, 2082
        start_year, end_year = 2063, 2097

    if args.cond:
        output_file = f'{output_dir}/{name_for_output_file}_{sim.lower()}_percentile_{start_year}-{end_year}_wetdays.nc'
    else:
        output_file = f'{output_dir}/{name_for_output_file}_{sim.lower()}_percentile_{start_year}-{end_year}.nc'
    if os.path.exists(output_file):
        os.remove(output_file)

    calculate_percentile(output_file, ds_variable, filenames, sim, start_year, end_year)

    # Example usage:
    # python /home/vdemeyer/DATA_COMPUTING/Calculate_Percentile.py --variable Wind --sim UBB
    # python /home/vdemeyer/DATA_COMPUTING/Calculate_Percentile.py --variable Precipitation --sim UBF --cond