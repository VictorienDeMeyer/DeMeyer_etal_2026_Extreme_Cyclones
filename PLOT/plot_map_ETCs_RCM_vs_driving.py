import json
import os
import gc
import numpy as np
import pandas as pd
import xarray as xr
from scipy.ndimage import binary_erosion
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

"""
Share of the CRCM6 biases with respect to ERA5 (historical period, 1980-2014) that comes from the regional
model and from the driving data, for the maps of Figs. 3 (PR) and 5 (WS) of the paper.

For each variable V (PR, WS) and each quantity X of these figures (difference of the cumulative exceedance
DeltaEE_cum|ETC, sum of its intensity and threshold terms, and its occurrence term, as plotted, factors
included):
  R   = X(UBB)            part of the bias specific to the RCM (UBB is CRCM6 driven by ERA5, the reference);
  D_S = X(S) - X(UBB)     part due to the driving data, for S = UBD (EC-Earth3-Veg), UBE (MPI-ESM1-2-HR) and
                          UBF (MIROC6), so that X(S) = R + D_S.
D_S also contains the sampling variability of 35 years of storms, since the years of the AOGCM-driven
simulations do not correspond to the observed years.

The values are those of the figures: the cells of plot_map_ETCs_diff_w_ERA5.ipynb (same folder) that come before
its first figure (imports, loading, plotting functions) are run as they are, then the cells of Figs. 3 and 5 up to
their savefig line, with the plotting function replaced by a stub that keeps its arguments (the plotted fields and
the map settings). The sum of the intensity and threshold terms, T_ERA5 * Delta(mean exceedance above the
threshold), is the field of the supplementary figures supp_term1&2_{PR,WS}_hist of the notebook.

Diagnostics, area-weighted (cos(latitude)) over the points shown in the figures (inside the map frame and the
CRCM6 domain, where at least one simulation shows a value; the other simulations count 0 there, as in the
notebook), for the whole domain, land and ocean (ERA5 land-sea mask, threshold 0.5), north and south of 40N, and
the points where EE_ERA5 exceeds 10% of its 99th percentile. Points with incomplete inputs are left out (about 2%,
mostly at the domain edge): regridded CRCM6 percentile 0, ERA5 percentile missing, or regridded count 0 with a
positive total (the intensity term is then undefined). The maps are drawn from the fields of the figures as they are.
  1. means of |R| and |D_S|, and f_RCM = sum|R| / (sum|R| + sum|D_S|);
  2. mean X(S)^2 = mean R^2 + mean D_S^2 + 2 mean R.D_S (each term);
  3. spatial correlation between R and X(S);
  4. standard deviation of X across UBD, UBE and UBF (ddof=1), mean compared with the mean of |R|.
Optional, projected changes (Figs. 7 and 8, plot_map_ETCs_diff_hist_w_future.ipynb, CRCM6 grid, total only):
|mean of the three changes| / standard deviation across them (ratio of the area means), and share of the points
where the three changes have the same sign. RCM and AOGCM cannot be separated in the projections.

Outputs (ALL/PLOT/RCM_VS_DRIVING/, suffix of the notebook, _noTC with tc_filter = 'phase'):
  - rcm_vs_driving_bias{tag}.csv : all the numbers (one row per value);
  - rcm_vs_driving_bias{tag}.md  : the same, as tables, with the checks;
  - {PR,WS}_bias_RCM_vs_driving{tag}.png : rows R, D_UBD, D_UBE, D_UBF and columns total, intensity + threshold,
    occurrence, with the projection, contours and colour scale of the total of Figs. 3 and 5, without hatching.

Usage: python plot_map_ETCs_RCM_vs_driving.py   (job: JOBS/plot_map_ETCs_RCM_vs_driving.sh)

Author: Dr Victorien De Meyer
Year: 2026
"""

PLOT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = '/home/vdemeyer/projects/rrg-gachon/vdemeyer'
OUT_DIR = f'{BASE}/ALL/PLOT/RCM_VS_DRIVING'
LSM = f'{BASE}/ALL/MASK/ERA5_lsm.nc'
DRIVING = {'UBD': 'EC-Earth3-Veg', 'UBE': 'MPI-ESM1-2-HR', 'UBF': 'MIROC6'}
TERMS = ['total', 'intensity', 'threshold', 'occurrence']           # columns of Figs. 3 and 5
QUANTITIES = ['total', 'intensity + threshold', 'occurrence']       # columns of the maps and tables
REGIONS = ['domain', 'land', 'ocean', 'north of 40N', 'south of 40N', 'EE_ERA5 > 10% of p99']
# Figure file stems (ALL/PLOT/<stem><tc_tag>.png) of the bias (Figs. 3, 5) and change (Figs. 7, 8) maps
BIAS_FIGURES = {'pr': 'PR_hist_vs_ERA5', 'ws': 'WS_hist_vs_ERA5'}
CHANGE_FIGURES = {'pr': 'PR_fut_vs_hist', 'ws': 'WS_fut_vs_hist'}
UNITS = {'pr': 'mm', 'ws': 'm s-1'}


def notebook_code(name):
    """Code cells of a figure notebook, without the IPython magics and shell lines."""
    with open(f'{PLOT_DIR}/{name}') as f:
        cells = json.load(f)['cells']
    return ['\n'.join(l for l in ''.join(c['source']).splitlines() if not l.lstrip().startswith(('%', '!')))
            for c in cells if c['cell_type'] == 'code']


def setup_notebook(name):
    """Runs the cells of a figure notebook that come before its first figure (imports, loading, plotting
    functions); returns its namespace and code cells."""
    cells = notebook_code(name)
    ns = {}
    for code in cells[:next(i for i, c in enumerate(cells) if 'savefig' in c)]:
        exec(code, ns)
    return ns, cells


def figure_call(ns, cells, stem, plot_function):
    """Runs the cell that saves ALL/PLOT/<stem><tc_tag>.png up to its savefig line, with the plotting function
    replaced by a stub, and returns the arguments of the plotting call."""
    target = f'/{stem}{{tc_tag}}.png'
    lines = next(c for c in cells if any(l.startswith('plt.savefig') and target in l for l in c.splitlines())).splitlines()
    code = '\n'.join(lines[:next(i for i, l in enumerate(lines) if l.startswith('plt.savefig') and target in l)])
    calls, real = [], ns[plot_function]
    ns[plot_function] = lambda *args, **kwargs: calls.append((args, kwargs))
    try:
        exec(code, ns)
    finally:
        ns[plot_function] = real
    (args, kwargs), = calls
    return args, kwargs


def visible_points(ns, field, var_lon, var_lat):
    """Grid points inside the map frame of the figures, with the projection and extent of the notebook."""
    assert field.dims == (var_lat, var_lon), field.dims
    fig, axes, crs = ns['_setup_plot_axes']([[0, 0, 1, 1]], figsize=(4, 4))
    ns['_draw_map_features'](axes[0])
    x, y, order = ns['_projected_grid'](axes[0], field, crs, var_lon, var_lat)
    x0, x1, y0, y1 = axes[0].get_extent()
    plt.close(fig)
    visible = np.empty(x.shape, dtype=bool)
    visible[:, order] = (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
    return visible


def wmean(a, w):
    return float((w * a).sum() / w.sum())


def bias_stats(R, X, w):
    """Diagnostics 1-3 of one driving simulation, over the selected points."""
    D = X - R
    sum_r, sum_d = float((w * np.abs(R)).sum()), float((w * np.abs(D)).sum())
    rc, xc = R - wmean(R, w), X - wmean(X, w)
    return {'mean_abs_X': wmean(np.abs(X), w), 'mean_abs_R': wmean(np.abs(R), w), 'mean_abs_D': wmean(np.abs(D), w),
            'f_RCM': sum_r / (sum_r + sum_d),
            'mean_X2': wmean(X ** 2, w), 'mean_R2': wmean(R ** 2, w), 'mean_D2': wmean(D ** 2, w),
            'two_mean_RD': 2 * wmean(R * D, w),
            'corr_R_X': wmean(rc * xc, w) / np.sqrt(wmean(rc ** 2, w) * wmean(xc ** 2, w))}


def plot_rcm_vs_driving(ns, fields, kwargs, var, path):
    """Maps of R = X(UBB) and D_S = X(S) - X(UBB) (rows) for the quantities of QUANTITIES (columns), drawn as
    plot_map_four_per_four draws Figs. 3 and 5 (same panels, projection, colour map and contours of EE_ERA5 on the
    total column), with three columns and without hatching. All columns take the colour scale of the total: the 3
    times wider scale of the intensity and threshold terms of the wind is for these two large terms that largely
    cancel, and their sum is of the same size as the total."""
    rcm, drivers = kwargs['sims'][0], kwargs['sims'][1:]
    rows = {'R': rcm, **{f'D_{s}': s for s in drivers}}
    panels = []
    for field in fields.values():
        panel = {'R': field[rcm]}
        for s in drivers:
            # As for the differences of the notebook: a missing value counts 0 when the other one is shown
            panel[f'D_{s}'] = (field[s].fillna(0) - field[rcm].fillna(0)).where(
                np.isfinite(field[s]) | np.isfinite(field[rcm]))
        panels.append(panel)
    # Contours of the figure (EE_ERA5) on the total column only, with the levels of the simulation of the row
    (cont,), (contour_levels,) = kwargs['cont'], kwargs['contour_levels']

    # Panels of the same size as in the 4 x 4 figures (16 x 16 in), on a 12 x 16 in figure
    ncols, nrows = len(panels), len(rows)
    width, gap = 0.23 * 4 / 3, 0.01 * 4 / 3
    positions = [[col * (width + gap), 0.83 - row * 0.26, width, 0.23] for row in range(nrows) for col in range(ncols)]
    fig, axes, crs = ns['_setup_plot_axes'](positions, figsize=(12, 16))

    V = var.upper()
    column_labels = [r'$\Delta EE_{' + V + r',cum|ETC}(x)$',
                     r'$T_{ETC}^{ERA5}(x) \cdot \Delta \overline{EE_{' + V + r'}}(x)$',
                     r'$\overline{EE_{' + V + r'}^{SIM}}(x) \cdot \Delta T_{ETC}(x)$']
    row_labels = [r'$R$: CRCM6$_{\mathbf{ERA5}}$ $-$ ERA5'] + [rf'$D$: {DRIVING[s]}' for s in drivers]
    for col, text in enumerate(column_labels):
        fig.text(positions[col][0] + width / 2, 0.83 + 0.23 + 0.01, text, ha='center', va='bottom', fontsize=20,
                 fontweight='bold')
    for row, text in enumerate(row_labels):
        fig.text(-0.005, positions[row * ncols][1] + 0.23 / 2, text, ha='right', va='center', fontsize=20,
                 fontweight='bold', rotation=90)

    for row_idx, (row, sim) in enumerate(rows.items()):
        for col_idx, panel in enumerate(panels):
            i = row_idx * ncols + col_idx
            ax = axes[i]
            ns['_draw_map_features'](ax)
            sc, levels = ns['_plot_data_on_ax'](
                ax, panel[row], crs, kwargs['style'], kwargs['colormap'], kwargs['vmin'], kwargs['vmax'], kwargs['step'],
                'both',
                cont=cont[sim] if col_idx == 0 else None, sigma=kwargs['sigma'],
                contour_levels=contour_levels[sim] if col_idx == 0 else None)
            ax.text(0, 1.01, f"$\\mathbf{{{chr(97 + i)})}}$", transform=ax.transAxes, fontsize=20, ha='left', va='bottom')

    label = (kwargs['label'].replace(' (CRCM6 $-$ ERA5)', '') + '\n'
             + r'$R$ = CRCM6$_{\mathrm{ERA5}}$ $-$ ERA5, $D$ = CRCM6$_{\mathrm{AOGCM}}$ $-$ CRCM6$_{\mathrm{ERA5}}$')
    cbar_ax = fig.add_axes([0, 0.01, positions[-1][0] + width, 0.025])
    ns['_add_cbar'](fig, sc, cbar_ax, label, kwargs['style'], levels)
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close('all')
    print(f'Saved {path}', flush=True)


def bias_part(rows, checks):
    ns, cells = setup_notebook('plot_map_ETCs_diff_w_ERA5.ipynb')
    tag = ns['tc_tag']
    with xr.open_dataset(LSM) as ds:
        lsm = ds['lsm'].squeeze(drop=True).load()
    lsm = lsm.assign_coords(longitude=lsm['longitude'] % 360).sortby('longitude')

    for var, stem in BIAS_FIGURES.items():
        print(f'\nBias {var}', flush=True)
        args, kwargs = figure_call(ns, cells, stem, 'plot_map_four_per_four')
        sims = kwargs['sims']
        assert sims == ['UBB'] + list(DRIVING), sims
        terms = dict(zip(TERMS, args[0]))
        fields = {'total': terms['total'],
                  'intensity + threshold': {s: terms['intensity'][s] + terms['threshold'][s] for s in sims},
                  'occurrence': terms['occurrence']}
        ref = fields['total']['UBB']
        lat, lon = ref['latitude'].values, ref['longitude'].values

        # Points shown in the figures: inside the map frame and the CRCM6 domain (mask of the notebook)
        visible = visible_points(ns, ref, 'longitude', 'latitude')
        domain = np.asarray(ns['mask'].squeeze())
        assert domain.shape == ref.shape, domain.shape
        n_out = int((visible & ~domain & np.isfinite(np.asarray(ref))).sum())
        checks.append(f'{var.upper()}: {n_out} points shown in Fig. {3 if var == "pr" else 5} (total, UBB) are outside '
                      f'the CRCM6 domain mask of the notebook; they are left out')

        # Points with complete inputs only: the regridded CRCM6 percentile is 0 at the domain edge, the ERA5
        # percentile is missing at a few points, and where the regridded count is 0 with a positive total
        # (conservative total, nearest-neighbour count) the intensity term is undefined (infinite in the notebook)
        q = dict(quantile=0.99, variable=var)
        name = {'pr': 'pr', 'ws': 'surf_wind'}[var]
        inputs = {s: {'total': np.asarray(ns['data']['total_ext_EETCs_total'][s].sel(**q)),
                      'count': np.asarray(ns['data']['count_ext_EETCs_total'][s].sel(**q)),
                      'perc': np.asarray(ns['per_regridded'][s, var].sel(quantile=0.99)[name])} for s in ['ERA5'] + sims}
        complete = np.isfinite(inputs['ERA5']['perc']) & np.all(
            [(inputs[s]['perc'] > 0) & ~((inputs[s]['count'] == 0) & (inputs[s]['total'] > 0)) for s in sims], axis=0)
        left_out = visible & domain & ~complete
        near_edge = domain & ~binary_erosion(domain, iterations=2)
        checks.append(f'{var.upper()}: {left_out.sum()} of the {(visible & domain).sum()} points shown inside the CRCM6 '
                      f'domain are left out (incomplete inputs), {(left_out & near_edge).sum()} of them within 2 grid '
                      f'cells of the domain edge: percentile of the 4 CRCM6 simulations 0 at '
                      f'{(visible & domain & (inputs["UBB"]["perc"] <= 0)).sum()}, ERA5 percentile missing at '
                      f'{(visible & domain & ~np.isfinite(inputs["ERA5"]["perc"])).sum()}, count 0 with a positive total '
                      f'(UBB, UBD, UBE, UBF) at '
                      + ', '.join(str((visible & domain & (inputs[s]['count'] == 0) & (inputs[s]['total'] > 0)).sum())
                                  for s in sims))

        land_frac = lsm.sel(latitude=xr.DataArray(lat, dims='latitude'),
                            longitude=xr.DataArray(lon % 360, dims='longitude'), method='nearest')
        assert np.allclose(land_frac['latitude'], lat, atol=1e-3) and np.allclose(land_frac['longitude'], lon % 360, atol=1e-3)
        lat2d = np.broadcast_to(lat[:, None], ref.shape)
        ee_era5 = np.asarray(ns['EEcum_era5'])
        threshold = 0.1 * np.nanpercentile(ee_era5[visible & domain & complete & (ee_era5 > 0)], 99)
        region_masks = {'domain': np.ones(ref.shape, bool), 'land': land_frac.values >= 0.5,
                        'ocean': land_frac.values < 0.5, 'north of 40N': lat2d >= 40, 'south of 40N': lat2d < 40,
                        'EE_ERA5 > 10% of p99': np.nan_to_num(ee_era5) > threshold}
        checks.append(f'{var.upper()}: EE_ERA5 threshold of the last region = {threshold:.1f} {UNITS[var]} '
                      f'(10% of the 99th percentile of the positive values shown)')
        weights = np.cos(np.deg2rad(lat2d))

        # Check: the totals of the figure are the ERA5 grid differences of EEcum recomputed from the inputs, and
        # the three terms add up to the total
        eecum = {s: np.nan_to_num(inputs[s]['total'] - inputs[s]['perc'] * inputs[s]['count']) for s in ['ERA5'] + sims}
        for s in sims:
            total = np.asarray(terms['total'][s])
            shown = np.isfinite(total)
            err = np.abs(total[shown] - (eecum[s] - eecum['ERA5'])[shown]).max()
            res = np.abs(total - sum(np.nan_to_num(np.asarray(terms[t][s])) for t in TERMS[1:]))
            res = res[shown & visible & domain & complete]
            checks.append(f'{var.upper()} {s}: total of the figure vs EEcum(sim) - EEcum(ERA5) recomputed, max abs '
                          f'difference {err:.1e} {UNITS[var]}; on the points kept, total - sum of the 3 terms exceeds '
                          f'1 {UNITS[var]} at {100 * (res > 1).mean():.2f}% of the points '
                          f'(max abs {res.max():.0f} {UNITS[var]}, mean abs {res.mean():.2f} {UNITS[var]})')

        for quantity in QUANTITIES:
            X = {s: np.asarray(fields[quantity][s]) for s in sims}
            shown = visible & domain & complete & np.any([np.isfinite(X[s]) for s in sims], axis=0)
            assert not np.any([np.isinf(X[s])[shown] for s in sims])
            X = {s: np.nan_to_num(x) for s, x in X.items()}
            for region in REGIONS:
                sel = shown & region_masks[region]
                w, R = weights[sel], X['UBB'][sel]
                base = dict(analysis='bias', variable=var.upper(), quantity=quantity, region=region)
                rows.append({**base, 'simulation': 'all', 'metric': 'n_points', 'value': int(sel.sum())})
                for s in DRIVING:
                    D = X[s][sel] - R
                    closure = np.abs(X[s][sel] - (R + D)).max()
                    if quantity == 'total' and region == 'domain':
                        checks.append(f'{var.upper()} {s}: max |X(S) - (R + D_S)| = {closure:.1e} {UNITS[var]}')
                    for metric, value in bias_stats(R, X[s][sel], w).items():
                        rows.append({**base, 'simulation': s, 'metric': metric, 'value': value})
                sd = np.std(np.stack([X[s][sel] for s in DRIVING]), axis=0, ddof=1)
                rows.append({**base, 'simulation': 'UBD,UBE,UBF', 'metric': 'mean_sd_drivers', 'value': wmean(sd, w)})
                rows.append({**base, 'simulation': 'UBD,UBE,UBF', 'metric': 'ratio_sd_to_abs_R',
                             'value': wmean(sd, w) / wmean(np.abs(R), w)})

        plot_rcm_vs_driving(ns, fields, kwargs, var, f'{OUT_DIR}/{var.upper()}_bias_RCM_vs_driving{tag}.png')
    return tag


def change_part(rows):
    ns, cells = setup_notebook('plot_map_ETCs_diff_hist_w_future.ipynb')
    for var, stem in CHANGE_FIGURES.items():
        print(f'\nChange {var}', flush=True)
        args, kwargs = figure_call(ns, cells, stem, 'plot_map_three_per_three')
        total = args[0][0]
        assert list(total) == list(DRIVING), list(total)
        ref = total['UBD']
        visible = visible_points(ns, ref, 'rlon', 'rlat')
        X = np.stack([np.asarray(total[s]) for s in DRIVING])
        shown = visible & np.isfinite(X).any(0)
        X = np.nan_to_num(X)[:, shown]
        w = np.broadcast_to(np.cos(np.deg2rad(ref['rlat'].values))[:, None], ref.shape)[shown]
        mean, sd = X.mean(0), X.std(0, ddof=1)
        base = dict(analysis='change', variable=var.upper(), quantity='total', region='domain', simulation='UBD,UBE,UBF')
        for metric, value in {'n_points': int(shown.sum()), 'mean_abs_mean_change': wmean(np.abs(mean), w),
                              'mean_sd_changes': wmean(sd, w), 'ratio_abs_mean_to_sd': wmean(np.abs(mean), w) / wmean(sd, w),
                              'same_sign_share': wmean((X > 0).all(0) | (X < 0).all(0), w)}.items():
            rows.append({**base, 'metric': metric, 'value': value})


def fmt(value):
    a = abs(value)
    return f'{value:.0f}' if a >= 100 else f'{value:.1f}' if a >= 1 else f'{value:.2f}'


def write_tables(rows, checks, tag):
    df = pd.DataFrame(rows)
    df['unit'] = [UNITS[v.lower()] if m.startswith(('mean_abs', 'mean_sd')) else
                  f'({UNITS[v.lower()]})2' if m in ('mean_X2', 'mean_R2', 'mean_D2', 'two_mean_RD') else ''
                  for v, m in zip(df['variable'], df['metric'])]
    df.to_csv(f'{OUT_DIR}/rcm_vs_driving_bias{tag}.csv', index=False)

    get = lambda **k: df.loc[np.logical_and.reduce([df[c] == v for c, v in k.items()]), 'value'].item()
    md = [f'# Share of the RCM and of the driving data in the CRCM6 biases ({tag or "all cyclones"}, 1980-2014)', '',
          'R = X(UBB) (CRCM6-ERA5 - ERA5), D = X(S) - X(UBB) for S = UBD (EC-Earth3-Veg), UBE (MPI-ESM1-2-HR), '
          'UBF (MIROC6), so that X(S) = R + D. X: total DeltaEE_cum|ETC, sum of the intensity and threshold terms, '
          'occurrence term. Area-weighted means over the points shown in Figs. 3 and 5 '
          '(ERA5 grid), without the points with incomplete inputs (see Checks). Columns: mean |X|, |R|, |D| in the unit of the variable; f_RCM = sum|R| / (sum|R| + sum|D|); '
          'mean X^2 = mean R^2 + mean D^2 + 2 mean RD, the last three in % of mean X^2; corr(R, X); '
          'sd/|R| = mean standard deviation of X across the three driving AOGCMs / mean |R| (same for the three rows '
          'of a region).', '']
    head = ('| Region | S | Points | mean abs X | mean abs R | mean abs D | f_RCM | mean X² | R² (%) | D² (%) | '
            '2RD (%) | corr(R, X) | sd/abs R |')
    for var in BIAS_FIGURES:
        V = var.upper()
        for quantity in QUANTITIES:
            md += [f'## {V}, {quantity} ({UNITS[var]})', '', head, '|' + '---|' * 13]
            for region in REGIONS:
                k = dict(analysis='bias', variable=V, quantity=quantity, region=region)
                for i, s in enumerate(DRIVING):
                    g = lambda m: get(**k, simulation=s, metric=m)
                    x2 = g('mean_X2')
                    md.append(f'| {region if i == 0 else ""} | {s} | {int(get(**k, simulation="all", metric="n_points")) if i == 0 else ""} | '
                              f'{fmt(g("mean_abs_X"))} | {fmt(g("mean_abs_R"))} | {fmt(g("mean_abs_D"))} | '
                              f'{100 * g("f_RCM"):.0f} % | {x2:.3g} | {100 * g("mean_R2") / x2:.0f} | '
                              f'{100 * g("mean_D2") / x2:.0f} | {100 * g("two_mean_RD") / x2:.0f} | '
                              f'{g("corr_R_X"):.2f} | '
                              f'{fmt(get(**k, simulation="UBD,UBE,UBF", metric="ratio_sd_to_abs_R")) if i == 0 else ""} |')
            md.append('')
    md += ['## Projected changes (Figs. 7 and 8, CRCM6 grid, total only)', '',
           'Ratio of the area means of |mean of the three changes| and of their standard deviation; share of the area '
           'where the three changes have the same sign (25% expected by chance for independent signs).', '',
           '| Variable | Points | mean abs(mean change) | mean sd | ratio | same sign |', '|---|---|---|---|---|---|']
    for var in CHANGE_FIGURES:
        k = dict(analysis='change', variable=var.upper())
        md.append(f'| {var.upper()} ({UNITS[var]}) | {int(get(**k, metric="n_points"))} | {fmt(get(**k, metric="mean_abs_mean_change"))} | '
                  f'{fmt(get(**k, metric="mean_sd_changes"))} | {get(**k, metric="ratio_abs_mean_to_sd"):.2f} | '
                  f'{100 * get(**k, metric="same_sign_share"):.0f} % |')
    md += ['', '## Checks', ''] + [f'- {c}' for c in checks] + ['']
    with open(f'{OUT_DIR}/rcm_vs_driving_bias{tag}.md', 'w') as f:
        f.write('\n'.join(md))
    print(f'Saved {OUT_DIR}/rcm_vs_driving_bias{tag}.csv and .md')


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rows, checks = [], []
    tag = bias_part(rows, checks)
    gc.collect()
    change_part(rows)
    print('\n'.join(checks))
    write_tables(rows, checks, tag)


if __name__ == '__main__':
    main()
