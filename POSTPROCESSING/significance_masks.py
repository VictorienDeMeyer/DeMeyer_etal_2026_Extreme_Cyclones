import argparse
import os
import pickle
import numpy as np
import xarray as xr
import xesmf as xe
from scipy import stats
from ETC_tools import tc_filter_tag

"""
Significance of the biases (CRCM6 - ERA5) and of the projected changes (future - historical) shown in the
maps of the paper, with respect to interannual variability.

At each grid point, the 35 annual (or seasonal) values of the two datasets are compared with a two-sided
Welch's t-test. The false discovery rate is controlled at ALPHA_FDR = 0.10 over the grid points of each map
(Benjamini and Hochberg, 1995), which corresponds to a global significance level of about 5% for spatially
correlated fields (Wilks, 2016, BAMS, doi:10.1175/BAMS-D-15-00267.1).

The tested quantities are those of the figure notebooks (plot_map_ETCs_diff_w_ERA5.ipynb and
plot_map_ETCs_diff_hist_w_future.ipynb), computed for each year:
  - EEcum, the cumulative exceedance above the 99th percentile attributed to cyclones,
    total - percentile x count (yearly outputs of contribution_ETCs.py), with the percentile of the dataset
    itself for the biases and that of the historical simulation for the changes;
  - the cyclone track density (yearly densities of calculate_kde.py <sim> YEARLY).
Biases are tested on the ERA5 grid, after the regridding of regrid_over_ERA5_grid.ipynb (conservative for the
totals, nearest neighbour for the counts, bilinear for the percentiles and densities); changes are tested on
the CRCM6 grid, as they are plotted.

Outputs (ALL/SIGNIFICANCE/), with variables EEcum_pr, EEcum_ws and density (1 where the difference is
significant, 0 elsewhere) and dims season (ALL, DJF, MAM, JJA, SON) x grid:
  - significance_bias{tag}.nc   : sim = UBB, UBD, UBE, UBF, on the ERA5 grid;
  - significance_change{tag}.nc : sim = UBD, UBE, UBF (historical member of each pair), on the CRCM6 grid.
The density masks are skipped (with a message) when the yearly densities are missing.

Usage: python significance_masks.py [--tc_filter phase]

Author: Dr Victorien De Meyer
Year: 2026
"""

BASE = '/home/vdemeyer/projects/rrg-gachon/vdemeyer'
OUT_DIR = f'{BASE}/ALL/SIGNIFICANCE'
QUANTILE = 0.99
ALPHA_FDR = 0.10
SEASONS = ['DJF', 'MAM', 'JJA', 'SON']
HIST_SIMS = ['UBB', 'UBD', 'UBE', 'UBF']
PAIRS = {'UBD': 'UBG', 'UBE': 'UBH', 'UBF': 'UBI'}
HIST_OF = {fut: hist for hist, fut in PAIRS.items()}
# folder, file name and variable name of each variable
VARIABLES = {'pr': ('PR', 'pr', 'pr'), 'ws': ('WIND', 'wind10', 'surf_wind')}


def years_of(sim):
    return range(2063, 2098) if sim in HIST_OF else range(1980, 2015)


def yearly_exceedance(sim, var, kind, tag):
    """Seasonal sum ('total') or count ('count') of the extreme exceedance attributed to cyclones for each
    year, dims (season, year, y, x)."""
    folder, file_var, name = VARIABLES[var]
    if sim == 'ERA5' and var == 'ws':
        folder = 'WIND/Magnitude'
    files = [f'{BASE}/{sim}/{folder}/1000km_storm/{kind}_{file_var}_ext_{sim.lower()}_1000hPa_1000km_extreme_storm_'
             f'{season}_{year}{tag}.nc' for year in years_of(sim) for season in SEASONS]
    with xr.open_mfdataset(files) as ds:
        da = ds[name].sel(quantile=QUANTILE, drop=True).load()
    return da.sel(season=SEASONS).transpose('season', 'year', ...)


def percentile(sim, var, regridded=False):
    folder, stem = ('PR_Percentile', 'pr') if var == 'pr' else ('WIND_Percentile', 'surf_wind')
    suffix = '_regridded_on_ERA5' if regridded else ''
    with xr.open_dataset(f'{BASE}/{sim}/{folder}/{stem}_{sim.lower()}_percentile_1980-2014{suffix}.nc') as ds:
        return ds[VARIABLES[var][2]].sel(quantile=QUANTILE, drop=True).load()


def with_annual(da):
    """Adds the annual sums as season 'ALL' to a (season, year, y, x) field (NaN kept outside the domain)."""
    return xr.concat([da.sum('season', skipna=False).expand_dims(season=['ALL']), da], dim='season')


def compute_bounds_2d(lat, lon):
    """Cell corners of a 2-D grid, as in regrid_over_ERA5_grid.ipynb (vectorised): mean of the four
    surrounding centres (circular mean for the longitudes), linearly extrapolated at the edges."""
    M, N = lat.shape
    lat_b = np.zeros((M + 1, N + 1))
    lon_b = np.zeros((M + 1, N + 1))
    lat_b[1:-1, 1:-1] = (lat[:-1, :-1] + lat[1:, :-1] + lat[:-1, 1:] + lat[1:, 1:]) / 4
    r = np.deg2rad(lon)
    s = (np.sin(r[:-1, :-1]) + np.sin(r[1:, :-1]) + np.sin(r[:-1, 1:]) + np.sin(r[1:, 1:])) / 4
    c = (np.cos(r[:-1, :-1]) + np.cos(r[1:, :-1]) + np.cos(r[:-1, 1:]) + np.cos(r[1:, 1:])) / 4
    lon_b[1:-1, 1:-1] = np.rad2deg(np.arctan2(s, c))
    for b in (lat_b, lon_b):
        b[0, :] = 2 * b[1, :] - b[2, :]
        b[-1, :] = 2 * b[-2, :] - b[-3, :]
        b[:, 0] = 2 * b[:, 1] - b[:, 2]
        b[:, -1] = 2 * b[:, -2] - b[:, -3]
    return lat_b, lon_b


def contribution_regridders(src, tgt):
    """Conservative and nearest-neighbour regridders from the CRCM6 grid to the ERA5 grid, and the domain mask
    on the ERA5 grid, as in regrid_over_ERA5_grid.ipynb."""
    lat, lon = src['lat'].values, src['lon'].values
    lat_b, lon_b = compute_bounds_2d(lat, lon)
    grid_src = xr.Dataset(coords={'lat': (('rlat', 'rlon'), lat), 'lon': (('rlat', 'rlon'), lon),
                                  'lat_b': (('rlat_b', 'rlon_b'), lat_b), 'lon_b': (('rlat_b', 'rlon_b'), lon_b)})
    lat2d, lon2d = np.meshgrid(tgt['latitude'].values, tgt['longitude'].values, indexing='ij')
    lat_bt, lon_bt = compute_bounds_2d(lat2d, lon2d)
    grid_tgt = xr.Dataset(coords={'latitude': tgt['latitude'].values, 'longitude': tgt['longitude'].values,
                                  'lat': (('latitude', 'longitude'), lat2d), 'lon': (('latitude', 'longitude'), lon2d),
                                  'lat_b': (('latitude_b', 'longitude_b'), lat_bt),
                                  'lon_b': (('latitude_b', 'longitude_b'), lon_bt)})
    conservative = xe.Regridder(grid_src, grid_tgt, method='conservative', periodic=True, ignore_degenerate=True)
    nearest = xe.Regridder(grid_src, grid_tgt, method='nearest_s2d')
    mask = conservative(xr.where(np.isfinite(src), 1.0, np.nan)).reset_coords(['lat', 'lon'], drop=True)
    return conservative, nearest, mask


def fdr_significant(a, b, valid):
    """Welch's t-test along the first axis (years) and false discovery rate control over the valid points."""
    with np.errstate(invalid='ignore', divide='ignore'):
        p = stats.ttest_ind(a, b, axis=0, equal_var=False).pvalue
    p = np.where(valid & np.isfinite(p), p, np.nan)
    p_sorted = np.sort(p[np.isfinite(p)])
    passed = p_sorted <= ALPHA_FDR * np.arange(1, p_sorted.size + 1) / max(p_sorted.size, 1)
    if not passed.any():
        return np.zeros(p.shape, dtype=np.int8)
    return (p <= p_sorted[passed].max()).astype(np.int8)


def test_maps(a, b, nonzero=True):
    """Significance mask (season, y, x) of the difference a - b between two (season, year, y, x) fields."""
    masks = []
    for season in a['season'].values:
        xa, xb = a.sel(season=season).values, b.sel(season=season).values
        valid = np.isfinite(xa).any(0) & np.isfinite(xb).any(0)
        xa, xb = np.nan_to_num(xa), np.nan_to_num(xb)
        if nonzero:
            # Points where neither dataset has cyclone-related extremes are not plotted
            valid &= (np.abs(xa.sum(0)) > 0) | (np.abs(xb.sum(0)) > 0)
        masks.append(fdr_significant(xa, xb, valid))
        print(f'    {season}: {100 * masks[-1].sum() / max(valid.sum(), 1):5.1f}% of {valid.sum()} points significant',
              flush=True)
    coords = {k: v for k, v in a.coords.items() if 'year' not in v.dims}
    return xr.DataArray(np.stack(masks), dims=a.dims[:1] + a.dims[2:], coords=coords)


def yearly_density(sim, tag):
    """Yearly track density (season, year, y, x), with the annual density as season 'ALL', or None."""
    path = f'{BASE}/{sim}/STORM_RELATED/DENSITY/density_ETCs_center_{sim.lower()}_yearly{tag}.nc'
    if not os.path.exists(path):
        return None
    with xr.open_dataset(path) as ds:
        dens, n_months = ds['density_ETCs'].load(), ds['n_months'].load()
    annual = (dens * n_months).sum('season', skipna=False) / n_months.sum('season')
    with xr.open_dataset(f'{BASE}/{sim}/STORM_RELATED/DENSITY/density_ETCs_center_{sim.lower()}_ALL{tag}.nc') as ds:
        full = ds['density_ETCs'].load()
    print(f'  {sim}: mean of the yearly densities vs full-period map, max relative difference '
          f'{float(np.nanmax(np.abs(annual.mean("year") - full)) / np.nanmax(full)):.1e}')
    return xr.concat([annual.expand_dims(season=['ALL']), dens.transpose('season', 'year', ...)], dim='season')


def save(masks, sims, path, grid_note):
    arrays = {name: xr.concat([m[sim] for sim in sims], dim=xr.DataArray(sims, dims='sim', name='sim'))
              for name, m in masks.items() if m}
    # All variables take the grid coordinates of the first one (same grid, read from different files)
    ref = next(iter(arrays.values()))
    ds = xr.Dataset({name: da.drop_vars([c for c in da.coords if c not in da.dims])
                     .assign_coords({d: ref[d].values for d in da.dims if d not in ('sim', 'season')})
                     for name, da in arrays.items()})
    ds = ds.assign_coords({c: ref[c] for c in ref.coords if c not in ref.dims})
    ds.attrs = {'description': '1 where the difference is significant with respect to interannual variability',
                'test': "two-sided Welch's t-test on the yearly (or seasonal) values",
                'multiple_testing': f'false discovery rate controlled at {ALPHA_FDR} over each map (Wilks, 2016)',
                'grid': grid_note}
    # Written next to the target and then renamed, as a notebook may hold the previous file open
    tmp = f'{path}.tmp'
    ds.to_netcdf(tmp, encoding={v: {'zlib': True, 'dtype': 'int8'} for v in ds.data_vars})
    os.replace(tmp, path)
    print(f'Saved {path}')


def main(tc_filter):
    tag = tc_filter_tag(tc_filter)
    os.makedirs(OUT_DIR, exist_ok=True)
    bias = {f'EEcum_{var}': {} for var in VARIABLES}
    change = {f'EEcum_{var}': {} for var in VARIABLES}

    # Cumulative extreme exceedance attributed to cyclones
    for var in VARIABLES:
        print(f'\n{var}', flush=True)
        total, count = yearly_exceedance('ERA5', var, 'total', tag), yearly_exceedance('ERA5', var, 'count', tag)
        era5 = with_annual(total - percentile('ERA5', var).values * count)
        if var == 'pr':
            conservative, nearest, mask = contribution_regridders(
                xr.open_dataset(f'{BASE}/UBB/WIND/1000km_storm/total_wind10_ubb_1000hPa_DJF_1980.nc')['surf_wind']
                .isel(season=0, year=0, drop=True), era5)
        native = {}
        for sim in HIST_SIMS + list(HIST_OF):
            total, count = yearly_exceedance(sim, var, 'total', tag), yearly_exceedance(sim, var, 'count', tag)
            if sim in PAIRS or sim in HIST_OF:
                native[sim] = with_annual(total - percentile(HIST_OF.get(sim, sim), var).values * count)
            if sim in HIST_SIMS:
                total_r = conservative(total).reset_coords(['lat', 'lon'], drop=True) * mask
                count_r = nearest(count).reset_coords(['lat', 'lon'], drop=True) * mask
                sim_r = with_annual(total_r - percentile(sim, var, regridded=True).values * count_r)
                sim_r = sim_r.assign_coords(latitude=era5['latitude'], longitude=era5['longitude'])
                print(f'  bias {sim}', flush=True)
                bias[f'EEcum_{var}'][sim] = test_maps(sim_r, era5)
        for hist, fut in PAIRS.items():
            print(f'  change {fut} - {hist}', flush=True)
            change[f'EEcum_{var}'][hist] = test_maps(native[fut], native[hist])

    # Check: the yearly files add up to the totals used by the figures
    with open(f'{BASE}/ALL/CONTRIB/contribution_ETCs_1000hPa_UBD_pr{tag}.pkl', 'rb') as f:
        ref = pickle.load(f)['total_ext_EETCs_total'].sel(quantile=QUANTILE)
    yearly_sum = yearly_exceedance('UBD', 'pr', 'total', tag).sum(['season', 'year'])
    print(f'\nCheck UBD pr: yearly files vs contribution total, max relative difference '
          f'{float(np.nanmax(np.abs(yearly_sum - ref)) / np.nanmax(ref)):.1e}')

    # Track density
    print('\ndensity', flush=True)
    dens = {sim: yearly_density(sim, tag) for sim in ['ERA5'] + HIST_SIMS + list(HIST_OF)}
    missing = [sim for sim, d in dens.items() if d is None]
    if missing:
        print(f'  Yearly densities missing for {missing}: density masks skipped '
              f'(run calculate_kde.py <sim> YEARLY first)')
    else:
        bias['density'], change['density'] = {}, {}
        src, tgt = dens['UBB'], dens['ERA5']
        bilinear = xe.Regridder(
            xr.Dataset(coords={'lat': (('rlat', 'rlon'), src['lat'].values), 'lon': (('rlat', 'rlon'), src['lon'].values)}),
            xr.Dataset(coords={'lat': ('latitude', tgt['latitude'].values), 'lon': ('longitude', tgt['longitude'].values)}),
            method='bilinear')
        for sim in HIST_SIMS:
            print(f'  bias {sim}', flush=True)
            sim_r = bilinear(dens[sim]).drop_vars(['lat', 'lon'], errors='ignore')
            bias['density'][sim] = test_maps(sim_r.assign_coords(latitude=dens['ERA5']['latitude'],
                                                                 longitude=dens['ERA5']['longitude']),
                                             dens['ERA5'], nonzero=False)
        for hist, fut in PAIRS.items():
            print(f'  change {fut} - {hist}', flush=True)
            change['density'][hist] = test_maps(dens[fut], dens[hist], nonzero=False)

    save(bias, HIST_SIMS, f'{OUT_DIR}/significance_bias{tag}.nc', 'ERA5 grid (CRCM6 regridded as in the figures)')
    save(change, list(PAIRS), f'{OUT_DIR}/significance_change{tag}.nc', 'CRCM6 grid')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Significance masks of the biases and projected changes')
    parser.add_argument('--tc_filter', type=str, default=None, choices=['phase', 'storm'],
                        help="Use the outputs without tropical cyclones: 'phase' = only the extratropical time steps, "
                             "'storm' = only the cyclones without any tropical phase")
    args = parser.parse_args()
    main(args.tc_filter)
