import os
import argparse
from glob import glob

import numpy as np
import pandas as pd
import xarray as xr
from scipy.spatial import cKDTree

from ETC_tools import open_df

"""
Cyclone phase space (CPS, Hart 2003) parameters along the tracked cyclones.

For one simulation and one year, this script computes at every track point at
00, 06, 12 and 18 UTC (CPS_HOURS) the following parameters:
  - B         : storm-motion-relative 900-600 hPa thickness asymmetry [m]
                B = h * [ mean(Z600 - Z900)|right - mean(Z600 - Z900)|left ]
                within RADIUS_KM of the center (h = +1 NH, -1 SH; right/left of
                the storm motion). B < 10 m: thermally symmetric (non-frontal).
  - minus_VTL : -V_T^L, lower-troposphere thermal wind parameter [m]
  - minus_VTU : -V_T^U, upper-troposphere thermal wind parameter [m]
                -V_T = d(dZ)/d(ln p), least-squares slope over the layer levels,
                with dZ(p) = max(Z(p)) - min(Z(p)) within RADIUS_KM of the center.
                -V_T > 0: warm core; -V_T < 0: cold core.

Deep warm core (-VTL > 0 and -VTU > 0) characterizes tropical cyclones, whereas
warm-seclusion extratropical cyclones only have a shallow warm core (-VTL > 0,
-VTU < 0) (Hart 2003). The labelling of each time step as tropical, transition or
extratropical is done afterwards by classify_cyclone_phase.py, after the 24-h
running mean of the parameters.

References:
  Hart (2003), MWR 131, 585-616.
  Evans and Hart (2003), MWR 131, 909-925.
  Bieli, Camargo, Sobel (2019), J. Climate 32, 3557-3582.
  Garin, Pausata, Boudreault, Ingrosso (2025), Weather Clim. Dynam. 6, 1379 (CPS with CRCM5/GEM at 0.12 deg).

Input geopotential height files (see GEOPOTENTIAL FILES below), one per month:
  - CRCM6 : {BASE}/{sim}/ZG/zg_{sim}_{YYYYMM}_se.nc, variable zg(time, plev, rlat, rlon)
  - ERA5  : {BASE}/ERA5/ZG/{YYYY}/{MM}/*.nc4, variable z(time, level, latitude, longitude)
Geopotential (m2 s-2), geopotential height (m) and GEM GZ (dam) are all accepted, as well
as pressure levels in Pa or hPa.

Output: {BASE}/{sim}/STORM_RELATED/CPS/cps_{sim}_{year}.csv

Author: Dr Victorien De Meyer
Year: 2026
"""

BASE = '/home/vdemeyer/projects/rrg-gachon/vdemeyer'

# Radius of the disk used for B and dZ (Hart 2003)
RADIUS_KM = 500.

# Pressure levels [hPa] used for -VTL and -VTU. Hart (2003) uses every 50 hPa between 900
# and 300 hPa, Garin et al. (2025) 900, 850, 800, 700, 600, 500, 400 and 300 hPa for
# CRCM5/GEM. The CRCM6 files have no 400 hPa level, so -VTU is fitted on 600, 500 and
# 300 hPa. The SAME levels must be used for ERA5 and the CRCM6 simulations so that the
# diagnostics are comparable.
LEVELS_LOWER = [900, 850, 800, 700, 600]
LEVELS_UPPER = [600, 500, 300]
# Bottom and top of the layer used for the thickness asymmetry B
B_BOTTOM, B_TOP = 900, 600

# Hours [UTC] at which the parameters are computed (6-hourly as in Hart 2003), whatever the
# frequency of the geopotential files, so that ERA5 and CRCM6 are treated identically
CPS_HOURS = [0, 6, 12, 18]

# Minimum fraction of the disk area covered by valid data (the disk can extend beyond the
# CRCM6 domain for centers close to its border). Below this fraction parameters are NaN.
MIN_COVERAGE = 0.5

# Half window [h] for the storm heading: bearing between the positions at t - 6 h and t + 6 h
HEADING_HALF_WINDOW_H = 6
# Displacement [km] below which the heading is considered undefined (quasi-stationary storm)
HEADING_MIN_DIST_KM = 1.

EARTH_RADIUS_KM = 6371.
G0 = 9.80665


# ----------------------------------------------------------------------------------------
# Geometry
# ----------------------------------------------------------------------------------------

def haversine(lon1, lat1, lon2, lat2):
    """Great circle distance [km] between points given in decimal degrees."""
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0., 1.)))


def bearing(lat1, lon1, lat2, lon2):
    """Initial bearing [deg, clockwise from north] from point 1 to point 2."""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = np.sin(dlon) * np.cos(lat2)
    y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dlon)
    return np.degrees(np.arctan2(x, y)) % 360.


def lonlat_to_xyz(lon, lat):
    """Unit vectors on the sphere, used for the KD-tree search."""
    lon, lat = np.radians(lon), np.radians(lat)
    return np.stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)], axis=-1)


def cell_area_km2(lat2d, lon2d):
    """Approximate area [km2] of each grid cell from the distances to its neighbours."""
    def spacing(axis):
        lat_a, lon_a = np.moveaxis(lat2d, axis, -1), np.moveaxis(lon2d, axis, -1)
        d = haversine(lon_a[..., 1:], lat_a[..., 1:], lon_a[..., :-1], lat_a[..., :-1])
        s = np.empty_like(lat_a)
        s[..., 1:-1] = 0.5 * (d[..., 1:] + d[..., :-1])
        s[..., 0] = d[..., 0]
        s[..., -1] = d[..., -1]
        return np.moveaxis(s, -1, axis)
    return spacing(0) * spacing(1)


class GridGeometry:
    """KD-tree and cell areas of a (possibly rotated) grid with 2D lat/lon."""

    def __init__(self, lat2d, lon2d):
        self.shape = lat2d.shape
        self.lat = lat2d.ravel()
        self.lon = lon2d.ravel()
        self.cell_area = cell_area_km2(lat2d, lon2d).ravel()
        self.tree = cKDTree(lonlat_to_xyz(self.lon, self.lat))

    def disk(self, lat0, lon0, radius_km):
        """Flat indices of the grid points within radius_km of (lat0, lon0)."""
        chord = 2. * np.sin(radius_km / (2. * EARTH_RADIUS_KM))
        return np.asarray(self.tree.query_ball_point(lonlat_to_xyz(lon0, lat0), chord), dtype=int)


def disk_area_km2(radius_km):
    """Area of a spherical cap of geodesic radius radius_km."""
    return 2. * np.pi * EARTH_RADIUS_KM**2 * (1. - np.cos(radius_km / EARTH_RADIUS_KM))


# ----------------------------------------------------------------------------------------
# Storm heading
# ----------------------------------------------------------------------------------------

def storm_headings(df, half_window_h=HEADING_HALF_WINDOW_H, min_dist_km=HEADING_MIN_DIST_KM):
    """
    Storm motion direction [deg, clockwise from north] at each track point: bearing from
    the position at t - half_window_h to the position at t + half_window_h (one-sided
    at the track ends). Undefined headings (quasi-stationary storm) are filled with the
    nearest defined heading of the same storm.
    """
    headings = pd.Series(np.nan, index=df.index)
    half = np.timedelta64(half_window_h, 'h')
    for _, g in df.sort_values(['storm', 'date']).groupby('storm', sort=False):
        t = g['date'].values
        lat, lon = g['lat'].values, g['lon'].values
        i_m = np.searchsorted(t, t - half, side='left')
        i_p = np.searchsorted(t, t + half, side='right') - 1
        h = bearing(lat[i_m], lon[i_m], lat[i_p], lon[i_p])
        h[haversine(lon[i_m], lat[i_m], lon[i_p], lat[i_p]) < min_dist_km] = np.nan
        headings.loc[g.index] = pd.Series(h, index=g.index).ffill().bfill().values
    return headings


# ----------------------------------------------------------------------------------------
# CPS parameters
# ----------------------------------------------------------------------------------------

def cps_parameters(z, levels, lat0, lon0, heading, geom,
                   levels_lower=LEVELS_LOWER, levels_upper=LEVELS_UPPER,
                   b_bottom=B_BOTTOM, b_top=B_TOP,
                   radius_km=RADIUS_KM, min_coverage=MIN_COVERAGE):
    """
    Hart (2003) parameters for one cyclone center at one time.

    :param z: geopotential height [m], array (n_levels, n_grid_points) (flattened grid).
    :param levels: pressure levels [hPa] of the first axis of z.
    :param lat0, lon0: cyclone center [deg].
    :param heading: storm motion direction [deg clockwise from north] (NaN -> B is NaN).
    :param geom: GridGeometry of the grid.
    :return: (B, minus_VTL, minus_VTU, coverage)
    """
    levels = list(levels)
    idx = geom.disk(lat0, lon0, radius_km)
    if idx.size == 0:
        return np.nan, np.nan, np.nan, 0.

    zd = z[:, idx]
    valid = np.all(np.isfinite(zd), axis=0)
    area = geom.cell_area[idx][valid]
    coverage = float(min(area.sum() / disk_area_km2(radius_km), 1.))
    if coverage < min_coverage:
        return np.nan, np.nan, np.nan, coverage
    zd = zd[:, valid]

    # Thermal asymmetry B (area-weighted semicircle means)
    B = np.nan
    if np.isfinite(heading):
        brg = bearing(lat0, lon0, geom.lat[idx][valid], geom.lon[idx][valid])
        side = np.sin(np.radians(brg - heading))   # > 0: right of the motion
        right, left = side > 0, side < 0
        if right.any() and left.any():
            thick = zd[levels.index(b_top)] - zd[levels.index(b_bottom)]
            hemi = 1. if lat0 >= 0 else -1.
            B = hemi * (np.average(thick[right], weights=area[right])
                        - np.average(thick[left], weights=area[left]))

    # Thermal wind parameters: slope of dZ = Zmax - Zmin against ln(p)
    dz = zd.max(axis=1) - zd.min(axis=1)

    def slope(layer_levels):
        k = [levels.index(p) for p in layer_levels]
        return np.polyfit(np.log(np.asarray(layer_levels, dtype=float)), dz[k], 1)[0]

    return B, slope(levels_lower), slope(levels_upper), coverage


# ----------------------------------------------------------------------------------------
# Geopotential files
# ----------------------------------------------------------------------------------------

def zg_files(sim, year, month):
    """Geopotential height files of one month."""
    if sim == 'ERA5':
        return sorted(glob(f'{BASE}/ERA5/ZG/{year}/{month:02d}/*.nc*'))
    return sorted(glob(f'{BASE}/{sim}/ZG/zg_{sim.lower()}_{year}{month:02d}_se.nc'))


def open_zg(files, levels, stride=1):
    """
    Open the geopotential height files of one month and standardize them.

    :param levels: required pressure levels [hPa].
    :return: (zg DataArray (time, plev, y, x) in m with plev in hPa, lat2d, lon2d)
    """
    ds = xr.open_mfdataset(files, combine='by_coords') if len(files) > 1 else xr.open_dataset(files[0])

    if 'valid_time' in ds.dims or 'valid_time' in ds.coords:
        ds = ds.rename({'valid_time': 'time'})
    for name in ('level', 'pressure_level', 'lev', 'pres'):
        if name in ds.dims:
            ds = ds.rename({name: 'plev'})

    var = next((v for v in ('zg', 'z', 'GZ', 'gz') if v in ds.data_vars), None)
    if var is None:
        raise KeyError(f'No geopotential variable (zg, z, GZ) in {files[0]}')
    zg = ds[var]

    # Units -> geopotential height [m]
    units = zg.attrs.get('units', '').replace('**', '').replace('^', '').strip()
    if units in ('m2 s-2', 'm2/s2', 'm2s-2', 'm+2 s-2'):
        zg = zg / G0
    elif units == 'dam':
        zg = zg * 10.
    elif units not in ('m', 'gpm', 'meters', 'metre', 'meter'):
        raise ValueError(f"Unknown geopotential units '{units}' in {files[0]}")

    # Pressure levels -> hPa
    plev = ds['plev'].values.astype(float)
    plev_units = ds['plev'].attrs.get('units', '').strip()
    if plev_units == 'Pa' or (plev_units == '' and plev.max() > 2000.):
        plev = plev / 100.
    zg = zg.assign_coords(plev=plev)
    missing = [p for p in levels if not np.any(np.isclose(plev, p))]
    if missing:
        raise ValueError(f'Missing pressure levels {missing} hPa in {files[0]} (available: {sorted(plev)})')
    levels = sorted(levels, reverse=True)
    zg = zg.sel(plev=levels, method='nearest').assign_coords(plev=np.array(levels, dtype=float))

    # Time -> pandas datetimes rounded to the hour (CRCM6 times carry float noise)
    time_index = zg.indexes['time']
    if not isinstance(time_index, pd.DatetimeIndex):
        time_index = time_index.to_datetimeindex()
    zg = zg.assign_coords(time=time_index.round('h'))

    # Horizontal grid
    if 'rlat' in zg.dims:
        ydim, xdim = 'rlat', 'rlon'
        lat2d, lon2d = ds['lat'].values, ds['lon'].values
    else:
        ydim = 'latitude' if 'latitude' in zg.dims else 'lat'
        xdim = 'longitude' if 'longitude' in zg.dims else 'lon'
        lon2d, lat2d = np.meshgrid(ds[xdim].values, ds[ydim].values)
    zg = zg.transpose('time', 'plev', ydim, xdim)

    if stride > 1:
        zg = zg.isel({ydim: slice(None, None, stride), xdim: slice(None, None, stride)})
        lat2d, lon2d = lat2d[::stride, ::stride], lon2d[::stride, ::stride]

    return zg, lat2d, lon2d


# ----------------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------------

def main(year, sim, stride):

    levels = sorted(set(LEVELS_LOWER) | set(LEVELS_UPPER) | {B_BOTTOM, B_TOP}, reverse=True)

    # Headings are computed on the full tracks so that storms crossing the year are handled
    df = open_df(sim, period_filtering=False)
    storms_year = df.loc[df['date'].dt.year == year, 'storm'].unique()
    df = df[df['storm'].isin(storms_year)].reset_index(drop=True)
    df['heading'] = storm_headings(df)
    df = df[df['date'].dt.year == year]
    print(f'{sim} {year}: {df["storm"].nunique()} storms, {len(df)} track points')

    records = []
    geom = None
    n_missing_time = 0

    for month in range(1, 13):

        df_month = df[df['date'].dt.month == month]
        if df_month.empty:
            continue

        files = zg_files(sim, year, month)
        if not files:
            raise FileNotFoundError(f'No geopotential file for {sim} {year}-{month:02d}')

        zg, lat2d, lon2d = open_zg(files, levels, stride=stride)
        zg_levels = [float(p) for p in zg['plev'].values]

        if geom is None:
            geom = GridGeometry(lat2d, lon2d)
            print(f'Grid {geom.shape}, mean cell size {np.sqrt(np.nanmean(geom.cell_area)):.1f} km')
        elif lat2d.shape != geom.shape:
            raise ValueError(f'Grid of {files[0]} differs from previous months')

        zg_times = pd.DatetimeIndex(zg['time'].values)
        track_times = pd.DatetimeIndex(df_month['date'].unique())
        track_times = track_times[track_times.hour.isin(CPS_HOURS)]
        times = track_times[track_times.isin(zg_times)]
        n_missing_time += len(track_times) - len(times)

        print(f'  {year}-{month:02d}: {len(times)} geopotential times with cyclones')
        if len(times) == 0:
            continue

        # Read the whole month before selecting the times: the CRCM6 files are chunked along
        # the whole month, so reading them time step by time step would decompress the same
        # chunks again at every step
        zg = zg.load().sel(time=times)

        for t in times:
            z = zg.sel(time=t).values.reshape(len(zg_levels), -1).astype(np.float64)
            for _, row in df_month[df_month['date'] == t].iterrows():
                center = (row['lat'], row['lon'], row['heading'], geom)
                B, vtl, vtu, cov = cps_parameters(z, zg_levels, *center)
                records.append({
                    'storm': row['storm'], 'date': t, 'lat': row['lat'], 'lon': row['lon'],
                    'heading': row['heading'], 'B': B, 'minus_VTL': vtl, 'minus_VTU': vtu,
                    'coverage': cov,
                })

        zg.close()

    if n_missing_time > 0:
        print(f'WARNING: {n_missing_time} track times missing in the geopotential files')

    columns = ['storm', 'date', 'lat', 'lon', 'heading', 'B', 'minus_VTL', 'minus_VTU', 'coverage']
    out = pd.DataFrame(records, columns=columns)
    output_dir = f'{BASE}/{sim}/STORM_RELATED/CPS'
    os.makedirs(output_dir, exist_ok=True)
    output_file = f'{output_dir}/cps_{sim}_{year}.csv'
    out.to_csv(output_file, index=False, float_format='%.4f', date_format='%Y-%m-%d %H:%M:%S')

    print(f'\nSaved {len(out)} points ({out["B"].notna().mean()*100:.1f}% with valid B, '
          f'{out["minus_VTL"].notna().mean()*100:.1f}% with valid -VT) to {output_file}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cyclone phase space (Hart 2003) parameters along the tracks')
    parser.add_argument('year', type=int, help='The year for which to process')
    parser.add_argument('--sim', type=str, required=True, help='Name of the simulation')
    parser.add_argument('--stride', type=int, default=1,
                        help='Use one grid point every STRIDE points in each direction (default 1: native grid). '
                             'E.g. 2 for CRCM6 (0.22 deg, close to the 0.25 deg ERA5 grid).')
    args = parser.parse_args()
    main(args.year, args.sim, args.stride)

# run /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/cyclone_phase_space.py 1985 --sim UBD
