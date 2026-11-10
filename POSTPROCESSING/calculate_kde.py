import xarray as xr
import pandas as pd
import numpy as np
from sklearn.neighbors import KernelDensity
from pyproj import Proj, Transformer, Geod
from pathlib import Path
import argparse
import sys
import os

"""
This script calculates the density of extratropical cyclone (ETC) centers per km² per month using Kernel Density Estimation (KDE).
It processes cyclone track data, projects coordinates to a Lambert Azimuthal Equal Area projection, computes KDE on a grid,
normalizes the density by the number of months, and saves the resulting density fields in NetCDF format.
The script supports seasonal filtering and can handle different simulation datasets (e.g., ERA5, UBF).
With --tc_filter phase, the tropical cyclones are excluded (see ETC_tools.open_df) and the
output filename carries the filter tag.
With season 'YEARLY', the density of each season of each year is computed with the same kernel and saved in a
single file (density_ETCs_center_{sim}_yearly.nc), for the significance tests (significance_masks.py). As the
bandwidth is fixed, the mean of these maps over the years equals the map of the full period.
"""

BANDWIDTH_KM = 200
SEASON_MONTHS = {'DJF': [12, 1, 2], 'MAM': [3, 4, 5], 'JJA': [6, 7, 8], 'SON': [9, 10, 11]}

def prepare_grid(for_coord, sim, transformer):
    """Prépare la grille et gère les noms de variables selon la simulation."""
    if sim == 'ERA5':
        lon_vals = for_coord['longitude'].values
        lat_vals = for_coord['latitude'].values
        grid_lon, grid_lat = np.meshgrid(lon_vals, lat_vals)
    else:
        grid_lat = for_coord['lat'].values
        grid_lon = for_coord['lon'].values
    
    grid_shape = grid_lat.shape
    gx, gy = transformer.transform(grid_lon.ravel(), grid_lat.ravel())
    grid_proj = np.vstack([gx, gy]).T
    return grid_lon, grid_lat, grid_shape, grid_proj

def save_density(dens_abs, sim, season, for_coord, grid_lat, grid_lon, output_dir, tc_tag=''):
    """Sauvegarde la densité finale en NetCDF avec les bonnes dimensions."""
    if sim == 'ERA5':
        coords = {"latitude": for_coord['latitude'].values, "longitude": for_coord['longitude'].values}
        dims = ("latitude", "longitude")
    else:
        coords = {
            "rlat": for_coord.rlat, 
            "rlon": for_coord.rlon,
            "lat": (("rlat", "rlon"), grid_lat),
            "lon": (("rlat", "rlon"), grid_lon)
        }
        dims = ("rlat", "rlon")

    da = xr.DataArray(
        dens_abs.astype(np.float32),
        dims=dims,
        coords=coords,
        name="density_ETCs",
        attrs={"units": "tracks / km² / month", "description": "KDE Cyclone Density"}
    )
    
    ds = da.to_dataset()
    if sim == 'ERA5':
        mask = xr.open_dataarray('/home/vdemeyer/projects/rrg-gachon/vdemeyer/ALL/MASK/mask_CRCM6_grid_for_ERA5.nc')
        ds = ds.where(mask, drop=True)
    output_path = output_dir / f"density_ETCs_center_{sim.lower()}_{season}{tc_tag}.nc"
    ds.to_netcdf(output_path)
    print(f"Fichier sauvegardé : {output_path}")

def yearly_densities(points_proj, dates, grid_proj, grid_shape):
    """Density of each season of each year [tracks / km² / month], with the kernel of the full-period maps."""
    years = np.unique(dates.year)
    dens = np.zeros((len(years), len(SEASON_MONTHS)) + grid_shape, dtype=np.float32)
    n_months = np.zeros((len(years), len(SEASON_MONTHS)), dtype=np.int32)
    for iy, year in enumerate(years):
        for js, months in enumerate(SEASON_MONTHS.values()):
            sel = np.asarray((dates.year == year) & dates.month.isin(months))
            if not sel.any():
                continue
            kde = KernelDensity(bandwidth=BANDWIDTH_KM * 1000, kernel="gaussian").fit(points_proj[sel])
            n_months[iy, js] = dates[sel].to_period("M").nunique()
            dens[iy, js] = np.exp(kde.score_samples(grid_proj)).reshape(grid_shape) * sel.sum() * 1e6 / n_months[iy, js]
        print(f"{year} done", flush=True)
    return years, dens, n_months

def save_yearly_densities(years, dens, n_months, sim, for_coord, grid_lat, grid_lon, output_dir, tc_tag=''):
    """Saves the yearly seasonal densities and their number of months (to rebuild annual densities)."""
    if sim == 'ERA5':
        coords = {"latitude": for_coord['latitude'].values, "longitude": for_coord['longitude'].values}
        dims = ("latitude", "longitude")
    else:
        coords = {"rlat": for_coord.rlat, "rlon": for_coord.rlon,
                  "lat": (("rlat", "rlon"), grid_lat), "lon": (("rlat", "rlon"), grid_lon)}
        dims = ("rlat", "rlon")
    coords.update({"year": years, "season": list(SEASON_MONTHS)})
    ds = xr.Dataset(
        {"density_ETCs": (("year", "season") + dims, dens,
                          {"units": "tracks / km² / month", "description": "KDE Cyclone Density of each season of each year"}),
         "n_months": (("year", "season"), n_months)},
        coords=coords)
    if sim == 'ERA5':
        mask = xr.open_dataarray('/home/vdemeyer/projects/rrg-gachon/vdemeyer/ALL/MASK/mask_CRCM6_grid_for_ERA5.nc')
        ds = xr.Dataset({"density_ETCs": ds["density_ETCs"].where(mask, drop=True), "n_months": ds["n_months"]})
    output_path = output_dir / f"density_ETCs_center_{sim.lower()}_yearly{tc_tag}.nc"
    ds.to_netcdf(output_path, encoding={"density_ETCs": {"zlib": True, "complevel": 4}})
    print(f"Fichier sauvegardé : {output_path}")

def main(sim, season, tc_filter=None):
    # 1. Chargement des données
    from ETC_tools import open_df, tc_filter_tag
    tracks = open_df(sim, period_filtering=True, tc_filter=tc_filter)

    coord_path = (
        '/home/vdemeyer/projects/rrg-gachon/vdemeyer/ERA5/PR_Percentile/pr_era5_percentile_1980-2014.nc'
        if sim == 'ERA5' else 
        '/home/vdemeyer/projects/rrg-gachon/vdemeyer/UBB/PR_Percentile/pr_ubb_percentile_1980-2014.nc'
    )
    for_coord = xr.open_dataset(coord_path)

    # 2. Projection
    proj = Proj(proj="laea", lat_0=45, lon_0=-100) # Lambert Azimuthal Equal Area (préserve les aires)
    transformer = Transformer.from_proj("epsg:4326", proj, always_xy=True)

    # 3. Filtrage des points
    lon, lat = tracks["lon"].values, tracks["lat"].values
    dates = pd.to_datetime(tracks["date"].values)

    if season == 'YEARLY':
        x, y = transformer.transform(lon, lat)
        grid_lon, grid_lat, grid_shape, grid_proj = prepare_grid(for_coord, sim, transformer)
        years, dens, n_months = yearly_densities(np.vstack([x, y]).T, dates, grid_proj, grid_shape)
        output_dir = Path(f"/project/rrg-gachon/vdemeyer/{sim}/STORM_RELATED/DENSITY")
        save_yearly_densities(years, dens, n_months, sim, for_coord, grid_lat, grid_lon, output_dir,
                              tc_filter_tag(tc_filter))
        return

    if season != 'ALL':
        s_mask = dates.month.isin(SEASON_MONTHS[season])
        lon, lat, dates = lon[s_mask], lat[s_mask], dates[s_mask]

    n_months = dates.to_period("M").nunique()
    n_tracks = len(lon)
    
    # Transformation des points en coordonnées projetées (mètres)
    x, y = transformer.transform(lon, lat)
    points_proj = np.vstack([x, y]).T

    # 4. Calcul KDE
    grid_lon, grid_lat, grid_shape, grid_proj = prepare_grid(for_coord, sim, transformer)
    
    kde = KernelDensity(bandwidth=BANDWIDTH_KM * 1000, kernel="gaussian")
    kde.fit(points_proj)
    
    # score_samples renvoie log(densité de probabilité). Intégrale de exp(log_dens) = 1
    log_dens = kde.score_samples(grid_proj)
    dens_prob = np.exp(log_dens).reshape(grid_shape)

    # 5. Normalisation Physique
    # dens_prob est en [1/m²]. On multiplie par N pour avoir [tracks/m²]
    dens_tracks_m2 = dens_prob * n_tracks
    
    # Conversion en [tracks / km² / month]
    dens_abs = (dens_tracks_m2 * 1e6) / n_months
    
    # 6. Sauvegarde
    output_dir = Path(f"/project/rrg-gachon/vdemeyer/{sim}/STORM_RELATED/DENSITY")
    output_dir.mkdir(parents=True, exist_ok=True)
    save_density(dens_abs, sim, season, for_coord, grid_lat, grid_lon, output_dir, tc_filter_tag(tc_filter))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('sim', type=str, default='ERA5')
    parser.add_argument('season', type=str, default='ALL')
    parser.add_argument('--tc_filter', type=str, default=None, choices=['phase'],
                        help="Exclude tropical cyclones: 'phase' = only the extratropical time steps")
    args = parser.parse_args()
    main(args.sim, args.season, args.tc_filter)

    # run /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/calculate_kde.py UBF JJA
    # . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_calculate_kde.sh