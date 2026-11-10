import argparse
import os
import numpy as np
import pandas as pd
import xarray as xr


"""
Adds a time step missing from the hourly CRCM6 outputs, by default 2030-04-01T00 of UBI (MIROC6, SSP3-7.0),
which was missing for the surface wind and the mean sea level pressure.

Same method as interpolate_missing_data_2015.py: the missing hour is filled by linear interpolation in time
between the last hour before it (end of the previous monthly file) and the first hour after it, and the monthly
file is rewritten with this hour added. Each variable is first checked: nothing is written when the time step is
already there (checked on 2026-11-10: 2030-04-01T00 is present in the wind, pressure and precipitation of UBI, the
gap has been filled upstream).

Usage: python interpolate_missing_data_UBI_2030.py [--sim UBI] [--time 2030-04-01T00]

Author: Dr Victorien De Meyer
Year: 2026
"""

BASE = '/home/vdemeyer/projects/rrg-gachon/vdemeyer'
# Hourly variables used by the chain: folder, file stem and variable name
VARIABLES = [('WIND', 'wind10', 'surf_wind'), ('PSL/RAW', 'psl', 'psl'), ('PR', 'pr', 'pr')]


def month_file(sim, folder, stem, t):
    return f'{BASE}/{sim}/{folder}/{stem}_{sim.lower()}_{t:%Y%m}_se.nc'


def hours(ds):
    # The CRCM6 times carry float noise: compare them rounded to the hour
    return pd.DatetimeIndex(ds['time'].values).round('h')


def fill_missing_hour(sim, folder, stem, var, missing):
    path = month_file(sim, folder, stem, missing)
    with xr.open_dataset(path) as ds:
        if missing in hours(ds):
            print(f'{sim} {var}: {missing} is present in {os.path.basename(path)}, nothing to do')
            return False
        ds = ds.load()

    # Neighbouring hours: the last one before the missing hour (end of the previous monthly file when the missing
    # hour is the first of the month) and the first one after it
    previous = month_file(sim, folder, stem, missing - pd.Timedelta('1h'))
    if previous != path:
        with xr.open_dataset(previous) as ds_prev:
            before = ds_prev.isel(time=np.flatnonzero(hours(ds_prev) < missing)[-1]).load()
    else:
        before = ds.isel(time=np.flatnonzero(hours(ds) < missing)[-1])
    k_after = np.flatnonzero(hours(ds) > missing)[0]
    after = ds.isel(time=k_after)
    t_before, t_after = hours(before.expand_dims('time'))[0], hours(after.expand_dims('time'))[0]
    if t_after - t_before != pd.Timedelta('2h'):
        raise ValueError(f'{sim} {var}: more than one hour missing around {missing} ({t_before} -> {t_after})')

    # Linear interpolation in time between the two neighbouring hours, for every variable with a time dimension
    # (the field and, for the precipitation, the time bounds)
    w = (missing - t_before) / (t_after - t_before)
    piece = ds.isel(time=[k_after]).copy(deep=True).assign_coords(time=[np.datetime64(missing, 'ns')])
    for name, da in ds.data_vars.items():
        if 'time' not in da.dims:
            continue
        b, a = before[name].values, after[name].values
        if np.issubdtype(da.dtype, np.datetime64):
            b, a = b.astype('int64'), a.astype('int64')
            piece[name].values[0] = np.round(b + w * (a - b)).astype('int64').astype(da.dtype)
        else:
            piece[name].values[0] = (b + w * (a - b)).astype(da.dtype)
    out = xr.concat([ds, piece], dim='time', data_vars='minimal', coords='minimal', compat='override').sortby('time')

    # Rewritten next to the original and then renamed, with the encoding of the original file
    keys = ('zlib', 'complevel', 'dtype', '_FillValue', 'units', 'calendar')
    encoding = {name: {k: v for k, v in ds[name].encoding.items() if k in keys}
                for name in list(ds.data_vars) + ['time']}
    tmp = f'{path}.tmp'
    out.to_netcdf(tmp, encoding=encoding)
    os.replace(tmp, path)
    print(f'{sim} {var}: {missing} added to {os.path.basename(path)} by linear interpolation '
          f'between {t_before} and {t_after}')
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Add a missing hourly time step by linear interpolation in time')
    parser.add_argument('--sim', type=str, default='UBI', help='Simulation (default UBI)')
    parser.add_argument('--time', type=str, default='2030-04-01T00', help='Missing time step (default 2030-04-01T00)')
    args = parser.parse_args()
    for folder, stem, var in VARIABLES:
        fill_missing_hour(args.sim, folder, stem, var, pd.Timestamp(args.time))
