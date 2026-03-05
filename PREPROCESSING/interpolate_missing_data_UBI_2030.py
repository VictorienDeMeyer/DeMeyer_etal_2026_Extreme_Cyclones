import xarray as xr
import numpy as np
import os


"""
Je dois rajouter une coordonnée à la variable surf_wind pour le 2030-04-01T00:00:00.000000000 qui est manquante pour le vent et la psl
"""

sim = ['UBI']     
filenames_wind = [f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/WIND/wind10_{sim.lower()}_203003_se.nc', f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/WIND/wind10_{sim.lower()}_203004_se.nc']
filenames_psl = [f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/PSL/psl_{sim.lower()}_203003_se.nc', f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/PSL/psl_{sim.lower()}_203004_se.nc']

for var, filenames in zip(['surf_wind', 'psl'], [filenames_wind, filenames_psl]):
    for files in filenames:
        ds = xr.open_mfdataset(filenames)
        ds = ds.sel(time=slice(f'2014-12-31', None))

    missing_time = np.datetime64('2015-01-01T00:00:00.000000')

    if ds_wind['time'].dt.round('h')[24] != missing_time:
        print(f"Timestamp 2015-01-01T00:00:00.000000 not found in wind data for {sim}. Inserting NaN values.")
        # Insert missing_time with NaN values
        new_times = np.sort(np.append(ds_wind['time'].values, missing_time))
        ds_wind = ds_wind.reindex({'time': new_times})
        # Interpolate only if there is a NaN at this timestamp
        surf_wind_at_missing = ds_wind['surf_wind'].sel(time=missing_time)
        if np.isnan(surf_wind_at_missing).any():
            ds_wind = ds_wind.chunk({'time': -1})
            ds_wind['surf_wind'] = ds_wind['surf_wind'].interpolate_na(dim='time', method='linear')
            print(f"Interpolation complete for {missing_time} in wind data.")

            ds_wind = ds_wind.sel(time=slice('2015-01-01', '2015-12-31'))
            ds_wind.to_netcdf(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/WIND/wind10_{sim.lower()}_201501_int_se.nc', mode='w')
            ds_wind.close()
            os.remove(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/WIND/wind10_{sim.lower()}_201501_se.nc')
            os.rename(
                f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/WIND/wind10_{sim.lower()}_201501_int_se.nc',
                f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/WIND/wind10_{sim.lower()}_201501_se.nc'
            )
            print(f"Processed and saved wind data for {sim} with interpolation for {missing_time}.")