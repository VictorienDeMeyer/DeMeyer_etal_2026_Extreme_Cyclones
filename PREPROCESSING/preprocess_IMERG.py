import argparse
import calendar
import os

import numpy as np
import pandas as pd
import xarray as xr

"""
Preparation of the IMERG precipitation (Final Run V07B, half-hourly, 0.1 degree) for the processing chain.
IMERG stays on its native grid; only the rows and columns of the grid that cover the CRCM6 domain are kept.

Three steps:
  - mask    : CRCM6 domain mask on the IMERG grid (ALL/MASK/mask_CRCM6_grid_for_IMERG.nc). An IMERG grid point
              is in the domain if its centre falls inside the CRCM6 grid (rotated coordinates within the
              rlat/rlon range, extended by half a grid cell).
  - month   : hourly precipitation of one month (IMERG/PR_1h/YYYY/MM/imerg_pr_ll_YYYYMM_1h.nc4), in mm/h,
              dims (time, latitude, longitude), NaN outside the domain.
              The IMERG time stamp is the start of the half-hour (00:00 = 00:00-00:29:59). The hourly value is
              labelled as in ERA5 (accumulation over the hour ending at the time stamp): the value at HH:00 is
              the mean of the half-hours HH-1:00 and HH-1:30, so the first hour of a month uses the last hour
              of the previous month. An hour is missing (NaN) if one of its two half-hours is missing.
              The numbers of missing half-hours and hours are written in IMERG/PR_1h/MISSING/.
  - missing : map of the fraction of missing half-hours and hours over a period
              (IMERG/PR_1h/imerg_missing_YYYY-YYYY.nc).

Usage:
  python preprocess_IMERG.py mask
  python preprocess_IMERG.py month --year 2001 --month 1
  python preprocess_IMERG.py missing --period 2001-2014

Author: Dr Victorien De Meyer
Year: 2026
"""

BASE = '/home/vdemeyer/projects/rrg-gachon/vdemeyer'
RAW = f'{BASE}/IMERG/PR'
OUT = f'{BASE}/IMERG/PR_1h'
MASK_FILE = f'{BASE}/ALL/MASK/mask_CRCM6_grid_for_IMERG.nc'
CRCM6_FILE = f'{BASE}/UBB/PR/pr_ubb_202001_se.nc'


def raw_file(year, month):
    return f'{RAW}/{year}/{month:02d}/imerg_v7_precipitation_ll_{year}{month:02d}_30m.nc4'


def hourly_file(year, month):
    return f'{OUT}/{year}/{month:02d}/imerg_pr_ll_{year}{month:02d}_1h.nc4'


def missing_file(year, month):
    return f'{OUT}/MISSING/missing_imerg_{year}{month:02d}.nc'


def make_mask():
    import cartopy.crs as ccrs

    with xr.open_dataset(raw_file(2001, 1)) as ds:
        lat, lon = ds['lat'].values, ds['lon'].values
    with xr.open_dataset(CRCM6_FILE) as ds:
        rlat, rlon = ds['rlat'].values, ds['rlon'].values
        pole = ds['rotated_pole'].attrs
    rotated = ccrs.RotatedPole(pole_longitude=pole['grid_north_pole_longitude'],
                               pole_latitude=pole['grid_north_pole_latitude'],
                               central_rotated_longitude=pole.get('north_pole_grid_longitude', 0.))
    lon2d, lat2d = np.meshgrid(lon.astype(np.float64), lat.astype(np.float64))
    pts = rotated.transform_points(ccrs.PlateCarree(), lon2d, lat2d)
    x, y = pts[..., 0], pts[..., 1]
    dx, dy = np.abs(np.diff(rlon)).mean() / 2, np.abs(np.diff(rlat)).mean() / 2
    inside = (x >= rlon.min() - dx) & (x <= rlon.max() + dx) & (y >= rlat.min() - dy) & (y <= rlat.max() + dy)
    mask = xr.DataArray(inside, coords={'latitude': lat, 'longitude': lon}, dims=('latitude', 'longitude'), name='mask')
    sub = mask.where(mask, drop=True)
    print(f'{int(mask.sum())} IMERG grid points in the CRCM6 domain, latitudes {float(sub.latitude.min())} to '
          f'{float(sub.latitude.max())}; kept rows x columns: {sub.latitude.size} x {sub.longitude.size}')

    # Check: the IMERG cell containing each CRCM6 grid point is in the mask
    with xr.open_dataset(CRCM6_FILE) as ds:
        clat, clon = ds['lat'].values.ravel(), ((ds['lon'].values.ravel() + 180) % 360) - 180
    i = np.clip(np.floor((clat - (lat[0] - 0.05)) / 0.1).astype(int), 0, lat.size - 1)
    j = np.clip(np.floor((clon - (lon[0] - 0.05)) / 0.1).astype(int), 0, lon.size - 1)
    print(f'Check: {100 * inside[i, j].mean():.3f}% of the CRCM6 grid points fall in an IMERG cell of the mask')

    os.makedirs(os.path.dirname(MASK_FILE), exist_ok=True)
    mask.to_netcdf(MASK_FILE)
    print(f'Saved {MASK_FILE}')


def domain_indices(mask):
    """Rows and runs of contiguous columns of the IMERG grid that cover the domain (as mask.where(mask, drop=True))."""
    rows = np.flatnonzero(mask.any('longitude').values)
    cols = np.flatnonzero(mask.any('latitude').values)
    assert np.all(np.diff(rows) == 1), 'the rows of the domain are not contiguous'
    runs = np.split(cols, np.flatnonzero(np.diff(cols) > 1) + 1)
    return slice(rows[0], rows[-1] + 1), [slice(r[0], r[-1] + 1) for r in runs]


def read_halfhours(path, tslice, rows, col_runs):
    with xr.open_dataset(path) as ds:
        da = ds['precipitation']
        parts = [da.isel(time=tslice, lat=rows, lon=c).load() for c in col_runs]
    return xr.concat(parts, dim='lon') if len(parts) > 1 else parts[0]


def make_month(year, month):
    mask = xr.open_dataarray(MASK_FILE)
    rows, col_runs = domain_indices(mask)
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)

    # Half-hours from the last hour of the previous month to the second to last half-hour of the month
    hh = xr.concat([read_halfhours(raw_file(prev_year, prev_month), slice(-2, None), rows, col_runs),
                    read_halfhours(raw_file(year, month), slice(0, -2), rows, col_runs)], dim='time')
    n_hours = calendar.monthrange(year, month)[1] * 24
    hours = pd.date_range(f'{year}-{month:02d}-01 00:00', periods=n_hours, freq='h')
    expected = pd.date_range(hours[0] - pd.Timedelta('1h'), periods=2 * n_hours, freq='30min')
    if not np.array_equal(pd.DatetimeIndex(hh['time'].values), expected):
        raise ValueError(f'Unexpected half-hours in {raw_file(year, month)} or the previous month')

    values = hh.values.reshape(n_hours, 2, *hh.shape[1:])
    pr = values.mean(axis=1)  # NaN if one of the two half-hours is missing
    dom = mask.isel(latitude=rows).sel(longitude=hh['lon'].values).values
    pr[:, ~dom] = np.nan

    coords = {'time': hours, 'latitude': hh['lat'].values, 'longitude': hh['lon'].values}
    ds = xr.Dataset({'pr': (('time', 'latitude', 'longitude'), pr)}, coords=coords)
    ds['pr'].attrs = {'units': 'mm/h', 'long_name': 'hourly precipitation',
                      'description': 'IMERG Final Run V07B (precipitation, formerly precipitationCal). Mean of the '
                                     'two half-hourly rates of the hour ending at the time stamp (ERA5 convention); '
                                     'NaN if one of them is missing, and outside the CRCM6 domain.'}
    ds['latitude'].attrs = {'units': 'degrees_north', 'standard_name': 'latitude'}
    ds['longitude'].attrs = {'units': 'degrees_east', 'standard_name': 'longitude'}
    ds.attrs = {'source': 'GPM IMERG Final Run V07B half-hourly (doi:10.5067/GPM/IMERG/3B-HH/07)',
                'history': 'PREPROCESSING/preprocess_IMERG.py (KATJA)'}

    out = hourly_file(year, month)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    encoding = {'pr': {'zlib': True, 'complevel': 4, 'shuffle': True, 'dtype': 'float32',
                       'chunksizes': (24, min(128, pr.shape[1]), min(128, pr.shape[2]))},
                'time': {'units': 'hours since 2000-01-01 00:00:00', 'dtype': 'float64'}}
    # Written next to the target and then renamed, so that an interrupted job leaves no partial file
    ds.to_netcdf(f'{out}.tmp', encoding=encoding)
    os.replace(f'{out}.tmp', out)
    print(f'Saved {out}')

    n_missing_hh = np.isnan(values).sum(axis=(0, 1)).astype(np.int16)
    n_missing_h = np.isnan(pr).sum(axis=0).astype(np.int16)
    miss = xr.Dataset({'n_missing_halfhours': (('latitude', 'longitude'), n_missing_hh),
                       'n_missing_hours': (('latitude', 'longitude'), n_missing_h)},
                      coords={'latitude': coords['latitude'], 'longitude': coords['longitude']},
                      attrs={'n_hours': n_hours})
    os.makedirs(os.path.dirname(missing_file(year, month)), exist_ok=True)
    miss.to_netcdf(missing_file(year, month))
    inside = n_missing_hh[dom]
    print(f'{year}-{month:02d}: {100 * inside.sum() / (2 * n_hours * inside.size):.3f}% of the half-hours and '
          f'{100 * n_missing_h[dom].sum() / (n_hours * inside.size):.3f}% of the hours missing in the domain; '
          f'max {np.nanmax(pr):.1f} mm/h')


def make_missing(period):
    start, end = map(int, period.split('-'))
    files = [missing_file(y, m) for y in range(start, end + 1) for m in range(1, 13)]
    absent = [f for f in files if not os.path.exists(f)]
    if absent:
        raise FileNotFoundError(f'{len(absent)} monthly files missing, e.g. {absent[0]}')
    n_hh, n_h, n_hours = 0, 0, 0
    for f in files:
        with xr.open_dataset(f) as ds:
            n_hh = n_hh + ds['n_missing_halfhours'].astype(np.int64).load()
            n_h = n_h + ds['n_missing_hours'].astype(np.int64).load()
            n_hours += ds.attrs['n_hours']
    dom = xr.open_dataarray(MASK_FILE).sel(latitude=n_h['latitude'], longitude=n_h['longitude'])
    out = xr.Dataset({'frac_missing_halfhours': (n_hh / (2 * n_hours)).where(dom).astype(np.float32),
                      'frac_missing_hours': (n_h / n_hours).where(dom).astype(np.float32)},
                     attrs={'period': period, 'n_hours': n_hours,
                            'description': 'Fraction of the half-hours and of the hours (missing if one of their two '
                                           'half-hours is missing) without IMERG data, CRCM6 domain only'})
    path = f'{OUT}/imerg_missing_{period}.nc'
    out.to_netcdf(path)
    print(f'Saved {path}')
    for lo, hi in [(0, 30), (30, 45), (45, 60), (60, 75), (75, 90)]:
        band = out.sel(latitude=slice(lo, hi))
        print(f'  {lo}-{hi}N: mean missing hours {100 * float(band.frac_missing_hours.mean()):.3f}%, '
              f'max {100 * float(band.frac_missing_hours.max()):.2f}%; points without any data: '
              f'{int((band.frac_missing_hours == 1).sum())}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Preparation of the IMERG precipitation')
    parser.add_argument('step', choices=['mask', 'month', 'missing'])
    parser.add_argument('--year', type=int)
    parser.add_argument('--month', type=int)
    parser.add_argument('--period', type=str, help='e.g. 2001-2014 (step missing)')
    args = parser.parse_args()
    if args.step == 'mask':
        make_mask()
    elif args.step == 'month':
        make_month(args.year, args.month)
    else:
        make_missing(args.period)
