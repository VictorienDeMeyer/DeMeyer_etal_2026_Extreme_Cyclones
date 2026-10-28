import os
import sys
import pickle
import argparse

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import cartopy.crs as ccrs
import cartopy.feature as cfeature

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'POSTPROCESSING'))
from ETC_tools import open_df

"""
Figures of the ERA5 test of the tropical cyclone exclusion (cyclone phase space).

  python plot_ERA5_TC_exclusion.py --fig cps          # phase space trajectories of named storms
  python plot_ERA5_TC_exclusion.py --fig validation   # labels against the IBTrACS nature
  python plot_ERA5_TC_exclusion.py --fig contribution # ETC contribution to extremes, with / without TCs
  python plot_ERA5_TC_exclusion.py --fig density      # ETC track density, with / without TCs

Inputs: outputs of classify_cyclone_phase.py, validate_phase_ibtracs.py, concat_contribution_ETCs.py
and calculate_kde.py (with and without --tc_filter phase).
Figures are saved in {BASE}/ALL/PLOT/TC_EXCLUSION/.

Author: Dr Victorien De Meyer
Year: 2026
"""

BASE = '/home/vdemeyer/projects/rrg-gachon/vdemeyer'
OUTPUT_DIR = f'{BASE}/ALL/PLOT/TC_EXCLUSION'

# Phase colours: categorical slots in a fixed order (validated for colour-vision deficiencies)
PHASE_COLORS = {'ETC': '#2a78d6', 'TC': '#eb6834', 'TRANSITION': '#1baf7a'}
PHASE_LABELS = {'TC': 'Tropical', 'TRANSITION': 'Transition', 'ETC': 'Extratropical'}

# CRCM6 rotated pole, used as map projection
MAP_PROJ = ccrs.RotatedPole(pole_longitude=83., pole_latitude=42.5)
# CRCM6 NAM-12 domain in rotated coordinates (rlon_min, rlon_max, rlat_min, rlat_max)
DOMAIN_EXTENT = [-31.85, 40.1, -34.6, 37.33]
B_CRIT = 10.

plt.rcParams.update({'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False})


def save(fig, name):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = f'{OUTPUT_DIR}/{name}'
    fig.savefig(path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {path}')


def map_axes(fig, position):
    ax = fig.add_subplot(*position, projection=MAP_PROJ)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.4, edgecolor='0.35')
    ax.add_feature(cfeature.BORDERS, linewidth=0.3, edgecolor='0.6')
    return ax


# ----------------------------------------------------------------------------------------
# Phase space trajectories
# ----------------------------------------------------------------------------------------

def find_storm(storms, name, year):
    sel = storms[storms['name'].fillna('').str.contains(name) & (pd.to_datetime(storms['start']).dt.year == year)]
    if sel.empty:
        raise ValueError(f'{name} {year} not found among the tracked storms paired with IBTrACS')
    return int(sel.index[0])


def plot_cps(track, examples, name='fig_ERA5_cps_examples.png'):
    """
    :param track: phase DataFrame (classify_cyclone_phase.py output).
    :param examples: list of (title, storm id).
    """
    fig = plt.figure(figsize=(11, 3.4 * len(examples)))
    for row, (title, storm) in enumerate(examples):
        g = track[track['storm'] == storm].sort_values('date')
        g6 = g[g['date'].dt.hour % 6 == 0]

        ax = map_axes(fig, (len(examples), 3, 3 * row + 1))
        ax.plot(g['lon'], g['lat'], color='0.7', linewidth=1, transform=ccrs.PlateCarree())
        for phase, color in PHASE_COLORS.items():
            p = g6[g6['phase'] == phase]
            ax.scatter(p['lon'], p['lat'], s=14, color=color, edgecolor='white', linewidth=0.4,
                       transform=ccrs.PlateCarree(), label=PHASE_LABELS[phase], zorder=3)
        pad = 8.
        ax.set_extent([g['lon'].min() - pad, g['lon'].max() + pad, g['lat'].min() - pad / 2, g['lat'].max() + pad / 2],
                      crs=ccrs.PlateCarree())
        ax.set_title(f'{title}: track', loc='left')
        if row == 0:
            ax.legend(loc='lower right', fontsize=7, frameon=False)

        for col, (x, y, xlabel, ylabel, xline, yline) in enumerate([
                ('minus_VTL', 'B', r'$-V_T^L$ (900-600 hPa)', 'B (m)', 0., B_CRIT),
                ('minus_VTL', 'minus_VTU', r'$-V_T^L$ (900-600 hPa)', r'$-V_T^U$ (600-300 hPa)', 0., 0.)]):
            ax = fig.add_subplot(len(examples), 3, 3 * row + 2 + col)
            ax.axvline(xline, color='0.6', linewidth=0.8)
            ax.axhline(yline, color='0.6', linewidth=0.8)
            ax.plot(g6[x], g6[y], color='0.75', linewidth=1, zorder=1)
            for phase, color in PHASE_COLORS.items():
                p = g6[g6['phase'] == phase]
                ax.scatter(p[x], p[y], s=18, color=color, edgecolor='white', linewidth=0.4, zorder=2)
            ax.annotate('start', (g6[x].iloc[0], g6[y].iloc[0]), xytext=(4, 4), textcoords='offset points',
                        fontsize=7, color='0.3')
            ax.annotate('end', (g6[x].iloc[-1], g6[y].iloc[-1]), xytext=(4, 4), textcoords='offset points',
                        fontsize=7, color='0.3')
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.set_title(f'{title}: ' + ('thermal symmetry' if col == 0 else 'thermal wind'), loc='left')
    fig.tight_layout()
    save(fig, name)


# ----------------------------------------------------------------------------------------
# Validation against IBTrACS
# ----------------------------------------------------------------------------------------

def plot_validation(sim='ERA5'):
    table = pd.read_csv(f'{BASE}/{sim}/STORM_RELATED/CPS/validation_ibtracs_points_{sim}.csv', index_col=0)
    natures = {'TS': 'Tropical (TS)', 'SS': 'Subtropical (SS)', 'ET': 'Extratropical (ET)', 'DS': 'Disturbance (DS)'}
    table = table.loc[[n for n in natures if n in table.index and table.loc[n].sum() > 0]]
    pct = table.div(table.sum(axis=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(6.5, 0.6 + 0.55 * len(pct)))
    left = np.zeros(len(pct))
    y = np.arange(len(pct))[::-1]
    for phase in ['TC', 'TRANSITION', 'ETC']:
        values = pct[phase].values
        ax.barh(y, values, left=left, height=0.6, color=PHASE_COLORS[phase], edgecolor='white',
                linewidth=2, label=PHASE_LABELS[phase])
        for k, (v, l) in enumerate(zip(values, left)):
            if v >= 8:
                ax.text(l + v / 2, y[k], f'{v:.0f}%', ha='center', va='center', fontsize=8, color='white')
        left += values
    ax.set_yticks(y)
    ax.set_yticklabels([f'{natures[n]}\nn = {int(table.loc[n].sum())}' for n in pct.index])
    ax.set_xlim(0, 100)
    ax.set_xlabel('Matched track points (%)')
    ax.set_title(f'{sim} phase labels of the cyclones matched to IBTrACS, by IBTrACS nature', loc='left')
    ax.legend(ncol=3, loc='lower center', bbox_to_anchor=(0.5, 1.08), frameon=False)
    save(fig, f'fig_{sim}_ibtracs_validation.png')


# ----------------------------------------------------------------------------------------
# Maps
# ----------------------------------------------------------------------------------------

def to_0_360(da):
    """Contiguous longitudes over the CRCM6 domain (174E-357E) for pcolormesh."""
    return da.assign_coords(longitude=da['longitude'] % 360).sortby('longitude')


def plot_triplet(fig, row, n_rows, fields, label, cmap, vmax, diff_max, diff_label):
    """Three maps: all cyclones, TCs excluded, difference."""
    titles = ['All tracked cyclones', 'Tropical cyclones excluded', 'Difference']
    data = [fields[0], fields[1], fields[1] - fields[0]]
    if diff_max is None:
        # Symmetric colour range from the data, so that small differences remain visible
        diff_max = float(np.nanpercentile(np.abs(data[2].values), 99)) or 1e-6
    for col in range(3):
        ax = map_axes(fig, (n_rows, 3, 3 * row + col + 1))
        ax.set_extent(DOMAIN_EXTENT, crs=MAP_PROJ)
        da = to_0_360(data[col])
        if col < 2:
            mesh = ax.pcolormesh(da['longitude'], da['latitude'], da, cmap=cmap, vmin=0, vmax=vmax,
                                 transform=ccrs.PlateCarree(), rasterized=True)
        else:
            mesh = ax.pcolormesh(da['longitude'], da['latitude'], da, cmap='RdBu_r',
                                 norm=mcolors.TwoSlopeNorm(0., -diff_max, diff_max),
                                 transform=ccrs.PlateCarree(), rasterized=True)
        ax.set_title(titles[col], loc='left')
        cb = fig.colorbar(mesh, ax=ax, orientation='horizontal', shrink=0.85, pad=0.03,
                          extend='max' if col < 2 else 'both')
        cb.set_label(label if col < 2 else diff_label, fontsize=8)


def plot_contribution(sim='ERA5', quantile=0.99, tc_tag='_noTC'):
    rows = []
    for var, name in [('pr', 'precipitation'), ('ws', 'surface wind')]:
        fields = []
        for tag in ['', tc_tag]:
            with open(f'{BASE}/ALL/CONTRIB/contribution_ETCs_1000hPa_{sim}_{var}{tag}.pkl', 'rb') as f:
                d = pickle.load(f)
            num = d['total_ext_EETCs_total'].sel(quantile=quantile, method='nearest')
            den = d['total_ext_total'].sel(quantile=quantile, method='nearest')
            fields.append((num / den.where(den > 0)) * 100.)
        rows.append((name, fields))

    fig = plt.figure(figsize=(11, 4.4 * len(rows)))
    for row, (name, fields) in enumerate(rows):
        plot_triplet(fig, row, len(rows), fields, f'ETC contribution to p{quantile*100:g} {name} (%)',
                     'Blues', 100, None, 'Difference (percentage points)')
    fig.tight_layout()
    save(fig, f'fig_{sim}_contribution_p{quantile*100:g}{tc_tag}.png')


def plot_density(sim='ERA5', seasons=('ALL', 'JJA', 'SON'), tc_tag='_noTC'):
    rows = []
    for season in seasons:
        fields = [xr.open_dataset(f'{BASE}/{sim}/STORM_RELATED/DENSITY/density_ETCs_center_{sim.lower()}_{season}{tag}.nc')
                  ['density_ETCs'] * 1e3 for tag in ['', tc_tag]]
        rows.append((season, fields))
    vmax = float(max(f[0].max() for _, f in rows))
    fig = plt.figure(figsize=(11, 4.4 * len(rows)))
    for row, (season, fields) in enumerate(rows):
        plot_triplet(fig, row, len(rows), fields, f'{season} cyclone density (10$^{{-3}}$ km$^{{-2}}$ month$^{{-1}}$)',
                     'Purples', vmax, None, 'Difference')
    fig.tight_layout()
    save(fig, f'fig_{sim}_density{tc_tag}.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Figures of the ERA5 tropical cyclone exclusion')
    parser.add_argument('--fig', type=str, required=True, choices=['cps', 'validation', 'contribution', 'density'])
    parser.add_argument('--sim', type=str, default='ERA5')
    args = parser.parse_args()

    if args.fig == 'cps':
        track = open_df(args.sim, period_filtering=True, tc_filter='phase', keep_non_etc=True)
        storms = pd.read_csv(f'{BASE}/{args.sim}/STORM_RELATED/CPS/validation_ibtracs_storms_{args.sim}.csv', index_col=0)
        examples = [(f'{n.title()} {y}', find_storm(storms, n, y)) for n, y in [('SANDY', 2012), ('IGOR', 2010)]]
        plot_cps(track, examples, name=f'fig_{args.sim}_cps_examples.png')
    elif args.fig == 'validation':
        plot_validation(args.sim)
    elif args.fig == 'contribution':
        plot_contribution(args.sim)
    else:
        plot_density(args.sim)

# python /home/vdemeyer/TRACKING/KATJA/PLOT/plot_ERA5_TC_exclusion.py --fig validation
