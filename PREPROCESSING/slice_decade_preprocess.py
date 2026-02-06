import xarray as xr
from glob import glob
import os
import argparse

"""
Script to combine the smoothed sea level pressure yearly NetCDF files into decadal files.
"""

def main(start_year, end_year, sim, mask_CRCM6):

    output_dir = f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/INPUTS/{sim}'

    filenames = []
    for year in range(start_year-1, end_year+1):
        # Use UBD files for UBG between 2010 and 2014, UBE for UBH, UBF for UBI
        alt_sim = None
        if sim == 'UBG' and 2010 <= year <= 2014:
            alt_sim = 'UBD'
        elif sim == 'UBH' and 2010 <= year <= 2014:
            alt_sim = 'UBE'
        elif sim == 'UBI' and 2010 <= year <= 2014:
            alt_sim = 'UBF'

        if alt_sim:
            filenames.extend(sorted(glob(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/INPUTS/{alt_sim}/{alt_sim}_psl_smoothed_400km_{year}_pres.nc')))
        else:
            filenames.extend(sorted(glob(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/INPUTS/{sim}/{sim}_{"CORDEX_NA_" if mask_CRCM6 else ""}psl_smoothed_400km_{year}_pres.nc')))
    
    ds = xr.open_mfdataset(filenames, chunks={'time': 120})

    if (sim == 'UBB' and start_year == 2020) or (sim == 'ERA5' and start_year == 2020) or (sim in ['UBD', 'UBE', 'UBF'] and start_year == 2010) or (sim in ['UBG', 'UBH'] and start_year == 2100) or (sim=='UBI' and start_year == 2090):
        ds_range = ds.sel(time=slice(f'{start_year-1}-12-01', None))
        filename = f'{output_dir}/{sim}_{"CORDEX_NA_" if mask_CRCM6 else ""}psl_smoothed_400km_{start_year}-{end_year}_1month_pres.nc'
    else:
        ds_range = ds.sel(time=slice(f'{start_year-1}-12-01', f'{end_year}-01-31'))
        filename = f'{output_dir}/{sim}_{"CORDEX_NA_" if mask_CRCM6 else ""}psl_smoothed_400km_{start_year}-{end_year-1}_1month_pres.nc'
    
    if os.path.exists(filename):
        # print(f'\n{start_year}-{end_year} single NetCDF file already exists')
        # continue
        os.remove(filename)

    print(f'\n\n{ds_range}')

    ds_range.to_netcdf(filename)

    print(f'\n\nCreated decadal file: {filename}\n\n############################\n\n')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Name of the simulation')
    parser.add_argument('sim', type=str, nargs='?', default='ERA5', help='Name of the simulation')
    parser.add_argument('--start_year', type=int, default=1979, help='Start year of the processing')
    parser.add_argument('--end_year', type=int, default=2100, help='End year of the processing')
    args = parser.parse_args()
    sim = args.sim
    start_year = args.start_year
    end_year = args.end_year

    if sim == 'ERA5':
        mask_CRCM6 = True
    else:
        mask_CRCM6 = False

    print(f'Processing simulation: {sim} from {start_year} to {end_year}, mask_CRCM6={mask_CRCM6}')

    main(start_year, end_year, sim, mask_CRCM6)
