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
import cartopy.crs as ccrs
import cartopy.feature as cfeature

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'POSTPROCESSING'))
from ETC_tools import open_df
import plot_style as S

"""
Figures of the ERA5 test of the tropical cyclone exclusion (cyclone phase space).

  python plot_ERA5_TC_exclusion.py --fig cps          # phase space trajectories of named storms
  python plot_ERA5_TC_exclusion.py --fig validation   # labels against the IBTrACS nature
  python plot_ERA5_TC_exclusion.py --fig ee           # EE_cum|ETC of precipitation and wind, with / without TCs
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
            if row == 0 and col == 0:
                handles = [plt.Line2D([], [], marker='o', linestyle='', color=c, label=PHASE_LABELS[p])
                           for p, c in PHASE_COLORS.items()]
                ax.legend(handles=handles, loc='upper left', fontsize=7, frameon=False)
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
# Maps (same style as the paper figures, see plot_style.py)
# ----------------------------------------------------------------------------------------

PANEL_TITLES = ['All tracked cyclones', 'Tropical cyclones excluded', 'Difference (b $-$ a)']


def nice_symmetric_range(diff, n_steps=5):
    """Symmetric colour range (1-2-2.5-5 x 10^k) covering the 99th percentile of |diff|."""
    p = float(np.nanpercentile(np.abs(diff.values), 99))
    if not np.isfinite(p) or p == 0:
        return 1., 1. / n_steps
    k = 10 ** np.floor(np.log10(p))
    vmax = next(m * k for m in (1., 2., 2.5, 5., 10.) if m * k >= p)
    return vmax, vmax / n_steps


def plot_row(fields, vmin, vmax, step, label, diff_label, name, tick_size=14):
    """Three maps: all cyclones (a), tropical cyclones excluded (b) and difference (c)."""
    positions = [[0.02, 0.25, 0.31, 0.70], [0.345, 0.25, 0.31, 0.70], [0.67, 0.25, 0.31, 0.70]]
    fig, axes, crs = S._setup_plot_axes(positions, figsize=(18, 8))
    data = [fields[0], fields[1], fields[1] - fields[0]]
    diff_max, diff_step = nice_symmetric_range(data[2])

    for i, ax in enumerate(axes):
        S._draw_map_features(ax)
        if i < 2:
            sc, levels = S._plot_data_on_ax(ax, data[i], crs, 'contourf', 'Spectral_r', vmin, vmax, step, 'max')
        else:
            sc_diff, levels_diff = S._plot_data_on_ax(ax, data[i], crs, 'contourf', 'coolwarm',
                                                      -diff_max, diff_max, diff_step, 'both')
        ax.text(0.02, 0.98, PANEL_TITLES[i], transform=ax.transAxes, fontsize=tick_size, fontweight='bold',
                ha='left', va='top', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.2'))
        ax.text(0, 1.02, f"$\\mathbf{{{chr(97 + i)})}}$", transform=ax.transAxes, fontsize=tick_size + 1,
                ha='left', va='bottom')

    S._add_cbar(fig, sc, fig.add_axes([0.02, 0.17, 0.635, 0.03]), label, 'contourf', levels,
                extend_opt='max', tick_size=tick_size)
    S._add_cbar(fig, sc_diff, fig.add_axes([0.69, 0.17, 0.29, 0.03]), diff_label, 'contourf', levels_diff,
                extend_opt='both', tick_size=tick_size)
    save(fig, name)


def ee_cum(sim, var, quantile, tag):
    """Accumulated exceedance above the percentile within 1000 km of an ETC (paper metric EE_cum|ETC)."""
    with open(f'{BASE}/ALL/CONTRIB/contribution_ETCs_1000hPa_{sim}_{var}{tag}.pkl', 'rb') as f:
        d = pickle.load(f)
    name, folder, prefix = {'pr': ('pr', 'PR_Percentile', 'pr'),
                            'ws': ('surf_wind', 'WIND_Percentile', 'surf_wind')}[var]
    threshold = xr.open_dataset(f'{BASE}/{sim}/{folder}/{prefix}_{sim.lower()}_percentile_1980-2014.nc')[name]
    threshold = threshold.sel(quantile=quantile, method='nearest')
    total = d['total_ext_EETCs_total'].sel(quantile=quantile, method='nearest')
    count = d['count_ext_EETCs_total'].sel(quantile=quantile, method='nearest')
    return total - threshold * count


def plot_ee(sim='ERA5', quantile=0.99, tc_tag='_noTC'):
    # Colour levels of the ERA5 panels of the paper (plot_map_ETCs_diff_w_ERA5.ipynb)
    settings = {
        'pr': (0, 2400, 300, r'$EE_{PR,cum|ETC}^{%s}(x)$ [mm]' % sim, '[mm]'),
        'ws': (0, 4250, 425, r'$EE_{WS,cum|ETC}^{%s}(x)$ [m$\cdot$s$^{-1}$]' % sim, r'[m$\cdot$s$^{-1}$]'),
    }
    for var, (vmin, vmax, step, label, unit) in settings.items():
        fields = [ee_cum(sim, var, quantile, tag) for tag in ['', tc_tag]]
        plot_row(fields, vmin, vmax, step, label, f'Difference {unit}',
                 f'fig_{sim}_EEcum_{var}_p{quantile * 100:g}{tc_tag}.png')


def plot_density(sim='ERA5', seasons=('ALL', 'JJA', 'SON'), tc_tag='_noTC'):
    unit = r'[tracks per $50 000~\mathrm{km^2}$ per month]'
    for season in seasons:
        fields = [xr.open_dataset(f'{BASE}/{sim}/STORM_RELATED/DENSITY/density_ETCs_center_{sim.lower()}_{season}{tag}.nc')
                  ['density_ETCs'] * 50000. for tag in ['', tc_tag]]
        if season == 'ALL':
            vmax, step = 5.5, 0.5   # levels of the paper figure
        else:
            vmax, _ = nice_symmetric_range(fields[0], n_steps=1)
            step = vmax / 10
        plot_row(fields, 0, vmax, step, f'{season} ETC trajectory density {unit}', f'Difference {unit}',
                 f'fig_{sim}_density_{season}{tc_tag}.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Figures of the ERA5 tropical cyclone exclusion')
    parser.add_argument('--fig', type=str, required=True, choices=['cps', 'validation', 'ee', 'density'])
    parser.add_argument('--sim', type=str, default='ERA5')
    args = parser.parse_args()

    if args.fig == 'cps':
        track = open_df(args.sim, period_filtering=True, tc_filter='phase', keep_non_etc=True)
        storms = pd.read_csv(f'{BASE}/{args.sim}/STORM_RELATED/CPS/validation_ibtracs_storms_{args.sim}.csv', index_col=0)
        examples = [(f'{n.title()} {y}', find_storm(storms, n, y)) for n, y in [('SANDY', 2012), ('IGOR', 2010)]]
        plot_cps(track, examples, name=f'fig_{args.sim}_cps_examples.png')
    elif args.fig == 'validation':
        plot_validation(args.sim)
    elif args.fig == 'ee':
        plot_ee(args.sim)
    else:
        plot_density(args.sim)

# python /home/vdemeyer/TRACKING/KATJA/PLOT/plot_ERA5_TC_exclusion.py --fig validation
