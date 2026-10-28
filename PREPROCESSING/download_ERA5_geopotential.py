import os
import time
import calendar
import argparse
import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import netCDF4

"""
Download the ERA5 geopotential on pressure levels needed by the cyclone phase space
(POSTPROCESSING/cyclone_phase_space.py): 300, 400, 500, 600, 700, 800, 850 and 900 hPa,
at 00, 06, 12 and 18 UTC, over 0-90N and 160E-360E (the CRCM6 domain spans 174E-357E).

Source: copy of ERA5 at the NCAR Research Data Archive (ds633.0, doi:10.5065/BH6N-5N20),
accessed through its THREDDS OPeNDAP server, which subsets the daily files server side
(no account needed).

Output, one file per month (same convention as the other ERA5 files):
  {BASE}/ERA5/ZG/{YYYY}/{MM}/era5_z_ll_{YYYYMM}_6h.nc4
  z(time, level, latitude, longitude) in m**2 s**-2 (float32, quantized to 1 m**2 s**-2,
  i.e. 0.1 m of geopotential height), level in hPa.

The download is network-bound and very light in CPU and memory, so it can run on a login
node (Narval compute nodes have no internet access). It is resumable: complete monthly
files are skipped and a month is written to a temporary file renamed at the end.

    nohup setsid python download_ERA5_geopotential.py --years 1980-2014 --workers 4 > download_ERA5_geopotential.log 2>&1 &

Author: Dr Victorien De Meyer
Year: 2026
"""

BASE = '/home/vdemeyer/projects/rrg-gachon/vdemeyer'
URL = ('https://thredds.rda.ucar.edu/thredds/dodsC/files/g/d633000/e5.oper.an.pl/{ym}/'
       'e5.oper.an.pl.128_129_z.ll025sc.{ymd}00_{ymd}23.nc')

LEVELS = [300, 400, 500, 600, 700, 800, 850, 900]   # hPa
HOURS = [0, 6, 12, 18]                              # UTC
LAT_MIN, LAT_MAX = 0., 90.
LON_MIN, LON_MAX = 160., 359.75                     # 0-360 convention

N_RETRY = 6


def output_file(year, month):
    return f'{BASE}/ERA5/ZG/{year}/{month:02d}/era5_z_ll_{year}{month:02d}_6h.nc4'


def read_day(day):
    """Subset of one daily file: (time, z, levels, lat, lon)."""
    url = URL.format(ym=day.strftime('%Y%m'), ymd=day.strftime('%Y%m%d'))
    for attempt in range(N_RETRY):
        try:
            with netCDF4.Dataset(url) as src:
                lev = src['level'][:].astype(float)
                lat = src['latitude'][:]
                lon = src['longitude'][:]
                hours = src['time'][:]   # hours since 1900-01-01
                k_lev = [int(np.where(np.isclose(lev, p))[0][0]) for p in LEVELS]
                k0, k1 = min(k_lev), max(k_lev)
                j = np.where((lat >= LAT_MIN) & (lat <= LAT_MAX))[0]
                i = np.where((lon >= LON_MIN) & (lon <= LON_MAX))[0]
                t = np.where(np.isin(hours % 24, HOURS))[0]
                if len(t) != len(HOURS) or np.any(np.diff(t) != t[1] - t[0]):
                    raise ValueError(f'Unexpected times in {url}: {hours}')
                # One request on the contiguous hull of the levels (fastest server side)
                z = src['Z'][t[0]:t[-1] + 1:t[1] - t[0], k0:k1 + 1, j[0]:j[-1] + 1, i[0]:i[-1] + 1]
                z = np.ma.filled(z, np.nan)[:, [k - k0 for k in k_lev]]
                return hours[t], z, np.array(LEVELS, dtype=float), lat[j], lon[i]
        except Exception as err:
            if attempt == N_RETRY - 1:
                raise
            wait = 30 * 2**attempt
            print(f'  retry {day:%Y-%m-%d} in {wait} s ({err})', flush=True)
            time.sleep(wait)


def download_month(year, month):
    out = output_file(year, month)
    if os.path.exists(out):
        return f'{year}-{month:02d} already exists'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + '.tmp'
    start = time.time()

    days = [datetime.date(year, month, d) for d in range(1, calendar.monthrange(year, month)[1] + 1)]
    with netCDF4.Dataset(tmp, 'w', format='NETCDF4') as dst:
        for n, day in enumerate(days):
            hours, z, lev, lat, lon = read_day(day)
            if n == 0:
                dst.createDimension('time', None)
                dst.createDimension('level', len(lev))
                dst.createDimension('latitude', len(lat))
                dst.createDimension('longitude', len(lon))
                v = dst.createVariable('time', 'i4', ('time',))
                v.units = 'hours since 1900-01-01 00:00:00.0'
                v.long_name = 'time'
                v.calendar = 'gregorian'
                v = dst.createVariable('level', 'i4', ('level',))
                v.units = 'millibars'
                v.long_name = 'pressure_level'
                v[:] = lev.astype('i4')
                v = dst.createVariable('latitude', 'f4', ('latitude',))
                v.units = 'degrees_north'
                v.long_name = 'latitude'
                v[:] = lat
                v = dst.createVariable('longitude', 'f4', ('longitude',))
                v.units = 'degrees_east'
                v.long_name = 'longitude'
                v[:] = lon
                v = dst.createVariable('z', 'f4', ('time', 'level', 'latitude', 'longitude'),
                                       zlib=True, complevel=2, least_significant_digit=0,
                                       chunksizes=(1, len(lev), len(lat), len(lon)))
                v.units = 'm**2 s**-2'
                v.long_name = 'Geopotential'
                v.standard_name = 'geopotential'
                dst.Conventions = 'CF-1.6'
                dst.source = 'ERA5 (ECMWF), NCAR RDA ds633.0 e5.oper.an.pl, doi:10.5065/BH6N-5N20'
                dst.history = (f'{datetime.datetime.now():%Y-%m-%d %H:%M}: subset of {URL} '
                               f'by download_ERA5_geopotential.py')
            k = len(dst['time'])
            dst['time'][k:k + len(hours)] = hours
            dst['z'][k:k + len(hours)] = z

    with netCDF4.Dataset(tmp) as check:
        if len(check['time']) != len(days) * len(HOURS):
            raise RuntimeError(f'Incomplete month in {tmp}')
    os.rename(tmp, out)
    return f'{year}-{month:02d} done in {time.time() - start:.0f} s'


def main(years, workers):
    months = [(y, m) for y in years for m in range(1, 13) if not os.path.exists(output_file(y, m))]
    print(f'{len(months)} months to download with {workers} workers', flush=True)
    failed = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(download_month, y, m): (y, m) for y, m in months}
        for future in as_completed(futures):
            y, m = futures[future]
            try:
                print(f'{datetime.datetime.now():%H:%M:%S} {future.result()}', flush=True)
            except Exception as err:
                failed.append((y, m))
                print(f'FAILED {y}-{m:02d}: {err}', flush=True)
                if os.path.exists(output_file(y, m) + '.tmp'):
                    os.remove(output_file(y, m) + '.tmp')
    print(f'Finished. {len(failed)} failed months: {failed}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download ERA5 geopotential on pressure levels for the cyclone phase space')
    parser.add_argument('--years', type=str, default='1980-2014', help='Year or range of years, e.g. 2012 or 1980-2014')
    parser.add_argument('--workers', type=int, default=4, help='Number of months downloaded in parallel')
    args = parser.parse_args()
    first, _, last = args.years.partition('-')
    main(range(int(first), int(last or first) + 1), args.workers)

# nohup setsid python /home/vdemeyer/TRACKING/KATJA/PREPROCESSING/download_ERA5_geopotential.py --years 1980-2014 --workers 4 > /home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/download_ERA5_geopotential.log 2>&1 &
