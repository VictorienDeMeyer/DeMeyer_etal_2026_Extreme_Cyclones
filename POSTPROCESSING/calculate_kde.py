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
"""

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

def save_density(dens_abs, sim, season, for_coord, grid_lat, grid_lon, output_dir):
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
        mask = xr.open_dataarray('/home/vdemeyer/projects/rrg-gachon/vdemeyer/MASK/mask_CRCM6_grid_for_ERA5.nc')
        ds = ds.where(mask, drop=True)
    output_path = output_dir / f"density_ETCs_center_{sim.lower()}_{season}.nc"
    ds.to_netcdf(output_path)
    print(f"Fichier sauvegardé : {output_path}")

def main(sim, season):
    # 1. Chargement des données
    from ETC_tools import open_files
    tracks, _ = open_files(sim, period_filtering=True)

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

    if season != 'ALL':
        months_dict = {'DJF': [12, 1, 2], 'MAM': [3, 4, 5], 'JJA': [6, 7, 8], 'SON': [9, 10, 11]}
        s_mask = dates.month.isin(months_dict[season])
        lon, lat, dates = lon[s_mask], lat[s_mask], dates[s_mask]

    n_months = dates.to_period("M").nunique()
    n_tracks = len(lon)
    
    # Transformation des points en coordonnées projetées (mètres)
    x, y = transformer.transform(lon, lat)
    points_proj = np.vstack([x, y]).T

    # 4. Calcul KDE
    grid_lon, grid_lat, grid_shape, grid_proj = prepare_grid(for_coord, sim, transformer)
    
    bandwidth_km = 200
    kde = KernelDensity(bandwidth=bandwidth_km * 1000, kernel="gaussian")
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
    output_dir = Path(f"/project/rrg-gachon/vdemeyer/{sim}/DENSITY")
    output_dir.mkdir(parents=True, exist_ok=True)
    save_density(dens_abs, sim, season, for_coord, grid_lat, grid_lon, output_dir)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('sim', type=str, default='ERA5')
    parser.add_argument('season', type=str, default='ALL')
    args = parser.parse_args()
    main(args.sim, args.season)

    # run /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/calculate_kde.py UBF JJA
    # . /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_calculate_kde.sh