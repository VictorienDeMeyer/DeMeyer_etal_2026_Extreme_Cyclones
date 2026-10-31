import argparse
import pickle
import sys
import numpy as np
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import cartopy.crs as ccrs

sys.path.insert(0, '/home/vdemeyer/TRACKING/KATJA/PLOT')
import plot_style as S

"""
Maps of the share of the cyclone-related extremes that is not due to extratropical cyclones:
which part of the extreme exceedance attributed to cyclones (contribution_ETCs.py, closest
cyclone within 1000 km) occurs while the cyclone is tropical or in transition.

The attribution gives each grid-point hour to a single cyclone, whose phase at that hour is
known (classify_cyclone_phase.py). The outputs without filter (all cyclones) and with
tc_filter='phase' (_noTC, extratropical time steps only) therefore give exactly:
    share of TC + transition = 1 - ETC / all cyclones.
No new computation is needed: the script only reads the contribution files of the two runs.

Figures (ALL/PLOT/TC_EXCLUSION/):
  - phase_share_hist   : ERA5 and the historical CRCM6 simulations;
  - phase_share_future : the future CRCM6 simulations.
Domain-wide shares are printed for the text.

Usage: python plot_cyclone_phase_share.py [--metric total|count] [--season ALL|DJF|MAM|JJA|SON]

Author: Dr Victorien De Meyer
Year: 2026
"""

CONTRIB = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/ALL/CONTRIB'
OUT_DIR = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/ALL/PLOT/TC_EXCLUSION'
QUANTILE = 0.99
HIST = ['ERA5', 'UBB', 'UBD', 'UBE', 'UBF']
FUTURE = ['UBG', 'UBH', 'UBI']
VARIABLES = {'pr': 'Precipitation', 'ws': 'Wind'}
SIM_LABEL = {
    'ERA5': r'ERA5',
    'UBB': r'CRCM6$_{\mathbf{ERA5}}$',
    'UBD': r'CRCM6$_{\mathbf{EC\text{-}Earth3\text{-}Veg}}$',
    'UBG': r'CRCM6$_{\mathbf{EC\text{-}Earth3\text{-}Veg}}$',
    'UBE': r'CRCM6$_{\mathbf{MPI\text{-}ESM1\text{-}2\text{-}HR}}$',
    'UBH': r'CRCM6$_{\mathbf{MPI\text{-}ESM1\text{-}2\text{-}HR}}$',
    'UBF': r'CRCM6$_{\mathbf{MIROC6}}$',
    'UBI': r'CRCM6$_{\mathbf{MIROC6}}$'
}
# Shares below the first level are not coloured, so that the background shows through
SHARE_LEVELS = [5, 10, 20, 30, 40, 50, 60, 80, 100]


def load_field(sim, var, tag, metric, season):
    """Cyclone-related extreme exceedance (sum or count over 35 years) above the 99th percentile."""
    key = f'{metric}_ext_EETCs_{"total" if season == "ALL" else "seasonal"}'
    with open(f'{CONTRIB}/contribution_ETCs_1000hPa_{sim}_{var}{tag}.pkl', 'rb') as f:
        da = pickle.load(f)[key].sel(quantile=QUANTILE)
    if season != 'ALL':
        da = da.sel(season=season)
    return da.load()


def non_etc_share(sim, var, metric, season):
    """Cyclone-related field and the share of it occurring during the TC and transition phases."""
    total = load_field(sim, var, '', metric, season)
    etc = load_field(sim, var, '_noTC', metric, season)
    valid = total > 0
    # The partition requires ETC <= all cyclones everywhere (same attribution, subset of hours)
    excess = (etc > total * (1 + 1e-6) + 1e-6) & valid
    if int(excess.sum()):
        print(f'WARNING {sim} {var}: ETC > all cyclones at {int(excess.sum())} grid points')
    return total, (1 - etc / total).where(valid).clip(0, 1)


def map_coords(da):
    """Plot coordinates and their projection (rotated pole for CRCM6, longitudes in 0-360 for ERA5)."""
    if 'rlat' in da.dims:
        rp = da.coords['rotated_pole'].attrs
        crs = ccrs.RotatedPole(pole_longitude=rp['grid_north_pole_longitude'],
                               pole_latitude=rp['grid_north_pole_latitude'])
        return da['rlon'].values, da['rlat'].values, da.values, crs
    da = da.assign_coords(longitude=da['longitude'] % 360).sortby('longitude')
    return da['longitude'].values, da['latitude'].values, da.values, ccrs.PlateCarree()


def cell_weights(da):
    """Grid-cell area weights: cos(latitude) for ERA5, uniform for the CRCM6 rotated grid."""
    if 'latitude' in da.dims:
        return np.cos(np.deg2rad(da['latitude'])) * xr.ones_like(da)
    return xr.ones_like(da)


def draw_share(ax, share):
    """Map of the share of TC + transition, with its 50% contour."""
    x, y, values, crs = map_coords(share * 100)
    cmap = plt.get_cmap('YlOrRd')
    norm = mcolors.BoundaryNorm(SHARE_LEVELS, cmap.N)
    mesh = ax.pcolormesh(x, y, np.where(values >= SHARE_LEVELS[0], values, np.nan), cmap=cmap, norm=norm,
                         transform=crs, shading='auto', zorder=1.5)
    ax.contour(x, y, values, levels=[50], colors='k', linewidths=0.8, transform=crs, zorder=2.5)
    return mesh


def make_grid(nrows, ncols, width=3.6, height=3.5):
    """Map axes on a regular grid, leaving room for row titles and a colour bar."""
    fig = plt.figure(figsize=(0.6 + ncols * width, 0.5 + nrows * height + 1.4))
    axes = np.empty((nrows, ncols), dtype=object)
    crs = ccrs.LambertConformal(central_latitude=45, central_longitude=-95)
    for r in range(nrows):
        for c in range(ncols):
            left = (0.6 + c * width) / fig.get_figwidth()
            bottom = (1.4 + (nrows - 1 - r) * height) / fig.get_figheight()
            ax = fig.add_axes([left, bottom, 0.97 * width / fig.get_figwidth(), 0.9 * height / fig.get_figheight()],
                              projection=crs)
            S._draw_map_features(ax)
            axes[r, c] = ax
    return fig, axes


def label_axes(fig, axes, sims, nrows):
    """Panel letters, simulation names (columns) and variables (rows)."""
    k = 0
    for r in range(nrows):
        for c, sim in enumerate(sims):
            ax = axes[r, c]
            ax.text(0, 1.02, f'({chr(97 + k)})', transform=ax.transAxes, fontsize=13, ha='left', va='bottom')
            if r == 0:
                ax.text(0.5, 1.08, SIM_LABEL[sim], transform=ax.transAxes, fontsize=12, ha='center', va='bottom')
            if c == 0:
                ax.text(-0.06, 0.5, list(VARIABLES.values())[r], transform=ax.transAxes, fontsize=14,
                        rotation=90, ha='right', va='center')
            k += 1


def share_figure(sims, shares, name, title_note):
    fig, axes = make_grid(len(VARIABLES), len(sims))
    for r, var in enumerate(VARIABLES):
        for c, sim in enumerate(sims):
            mesh = draw_share(axes[r, c], shares[(sim, var)][1])
    label_axes(fig, axes, sims, len(VARIABLES))
    cax = fig.add_axes([0.25, 0.06, 0.5, 0.025])
    cb = fig.colorbar(mesh, cax=cax, orientation='horizontal', ticks=SHARE_LEVELS)
    cb.set_label(f'Share of the cyclone-related extreme exceedance occurring in tropical or transition phase (%){title_note}',
                 fontsize=12)
    cb.ax.tick_params(labelsize=11)
    fig.savefig(f'{OUT_DIR}/{name}.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {OUT_DIR}/{name}.png')


def print_domain_shares(shares):
    """Shares weighted by the exceedance and the cell area, over the domain and by latitude band, for the text."""
    bands = [(0, 30), (30, 40), (40, 50), (50, 90)]
    print('\nShare of the cyclone-related extreme exceedance in TC + transition phase (%)')
    print(f'{"":5s} {"var":3s} {"domain":>7s} ' + ' '.join(f'{f"{a}-{b}N":>7s}' for a, b in bands))
    for (sim, var), (total, share) in shares.items():
        lat = total['lat'] if 'lat' in total.coords else total['latitude'] * xr.ones_like(total)
        w = cell_weights(total) * total.fillna(0)
        cells = []
        for a, b in [(-90, 90)] + bands:
            sel = (lat >= a) & (lat < b) & np.isfinite(share)
            ref = float((w * sel).sum())
            cells.append(100 * float((w * share.fillna(0) * sel).sum()) / ref if ref else np.nan)
        print(f'{sim:5s} {var:3s} ' + ' '.join(f'{c:7.1f}' for c in cells))


def main(metric, season):
    shares = {(sim, var): non_etc_share(sim, var, metric, season) for sim in HIST + FUTURE for var in VARIABLES}
    print_domain_shares(shares)
    suffix = ('' if metric == 'total' else f'_{metric}') + ('' if season == 'ALL' else f'_{season}')
    note = '' if season == 'ALL' else f', {season}'
    share_figure(HIST, shares, f'phase_share_hist{suffix}', note)
    share_figure(FUTURE, shares, f'phase_share_future{suffix}', note)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Maps of the share of the cyclone-related extremes not due to ETCs')
    parser.add_argument('--metric', type=str, default='total', choices=['total', 'count'],
                        help='total: accumulated exceedance; count: number of exceedance hours')
    parser.add_argument('--season', type=str, default='ALL', choices=['ALL', 'DJF', 'MAM', 'JJA', 'SON'])
    args = parser.parse_args()
    main(args.metric, args.season)
