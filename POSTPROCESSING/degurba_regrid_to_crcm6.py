"""
Extract and regrid the GHS-SMOD raster (1 km Mollweide) onto the CRCM6
rotated-pole grid, producing per-class fraction-of-coverage fields.

GHS-SMOD (Settlement MODel, JRC release R2023A V2.0, epoch E2025) is the
canonical DEGURBA classification raster: each 1 km pixel is assigned to one of
the 7 Level-2 settlement classes (11/12/13 = rural levels, 21/22/23 = urban
cluster levels, 30 = urban centre). The numerical encoding follows the
official EU/UN DEGURBA manual.

Why this approach works (and why we do NOT need xesmf here)
-----------------------------------------------------------
The source SMOD raster is in Mollweide projection (EPSG:54009), which is an
EQUAL-AREA projection: every 1 km pixel represents exactly 1 km^2 on Earth.
We want, for each CRCM6 cell, the fraction of that cell covered by each
DEGURBA class. If we turn the SMOD raster into a binary field per class
(1 where pixel == class C, 0 elsewhere) and reproject it with
`Resampling.average`, the output value in a target cell is the mean of all
source pixels falling inside that cell. Because source pixels are equal-area,
this mean is exactly:

    (# km^2 belonging to class C in the target cell) / (# km^2 covered)
    = fraction of the target cell covered by class C

This is mathematically equivalent to conservative area-weighted regridding,
but implemented purely with GDAL's warper via rioxarray -- simpler and
rock-solid.

The CRCM6 grid is a rotated-pole grid (CF grid_mapping_name =
"rotated_latitude_longitude"). pyproj understands this natively via
`CRS.from_cf(...)`, so we can reproject directly from Mollweide to rotated
pole without ever going through a regular lat/lon grid. This also fully
avoids the dateline issue: in rotated-pole coords the North-American domain
is a simple connected rectangle.

Output NetCDF content
---------------------
For each DEGURBA Level-2 class (11, 12, 13, 21, 22, 23, 30) we save a 2D
(rlat, rlon) variable named `frac_class<NN>` with values in [0, 1].
We also derive Level-1 grouped fractions for convenience:
    frac_L1_rural         = frac_class11 + frac_class12 + frac_class13
    frac_L1_urban_cluster = frac_class21 + frac_class22 + frac_class23
    frac_L1_urban_centre  = frac_class30

Run
---
module purge
module load StdEnv/2023 python/3.11 scipy-stack/2024a gdal/3.7.2
source ~/env_geo/bin/activate
python ~/TRACKING/KATJA/POSTPROCESSING/degurba_regrid_to_crcm6.py

Author: generated for Dr Victorien De Meyer
"""

import os
import zipfile

import numpy as np
import xarray as xr
import rioxarray  # noqa: F401  (registers .rio accessor on xarray objects)
from rasterio.enums import Resampling
from pyproj import CRS


# ---------------------------------------------------------------------------
# Constants: paths and DEGURBA class codes
# ---------------------------------------------------------------------------

MASK_DIR = "/home/vdemeyer/projects/rrg-gachon/vdemeyer/ALL/MASK"

# GHS-SMOD R2023A V2.0 archive basename (file stem inside MASK_DIR, without
# extension). E2025 epoch is the JRC nowcast/observed settlement reference.
ARCHIVE_STEM = "GHS_SMOD_E2025_GLOBE_R2023A_54009_1000_V2_0"

# Reference CRCM6 NetCDF: we read rlat/rlon and the rotated_pole attrs from it.
# All CRCM6 simulations (UBB, UBD, UBE, UBF, UBG, UBH, UBI) share the same grid,
# so any one of them works as reference.
CRCM6_REF_NC = (
    "/home/vdemeyer/projects/rrg-gachon/vdemeyer/UBD/PR/pr_ubd_197909_se.nc"
)

# DEGURBA Level-2 class codes (see GHSL_Data_Package_2023.pdf shipped in zip).
# 30 = Urban Centre, 23 = Dense Urban Cluster, 22 = Semi-dense Urban Cluster,
# 21 = Suburban/peri-urban, 13 = Rural Cluster (village),
# 12 = Low density rural, 11 = Very low density rural.
# (10 = water is ignored: no settlement.)
DEGURBA_CLASSES = [11, 12, 13, 21, 22, 23, 30]

# Level-1 groupings (used for the derived variables)
L1_GROUPS = {
    "L1_rural":         [11, 12, 13],
    "L1_urban_cluster": [21, 22, 23],
    "L1_urban_centre":  [30],
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():

    # -----------------------------------------------------------------------
    # 1) Locate and unzip the SMOD archive (if not already extracted)
    # -----------------------------------------------------------------------
    zip_name = f"{ARCHIVE_STEM}.zip"
    zip_path = os.path.join(MASK_DIR, zip_name)
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"Archive not found: {zip_path}")

    # Extract next to the zip, into a dedicated subdirectory
    extract_dir = os.path.join(MASK_DIR, "DEGURBA_E2025")
    tif_name = f"{ARCHIVE_STEM}.tif"
    tif_path = os.path.join(extract_dir, tif_name)

    if not os.path.exists(tif_path):
        print(f"Extracting {zip_path} -> {extract_dir}")
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)
    else:
        print(f"TIFF already extracted: {tif_path}")

    # -----------------------------------------------------------------------
    # 2) Open the SMOD GeoTIFF lazily with rioxarray
    #
    # `open_rasterio` returns an xarray.DataArray with:
    #   - dims (band, y, x)   -- single band here, so we squeeze
    #   - coords x, y in Mollweide meters (EPSG:54009)
    #   - a .rio accessor giving CRS, transform, nodata, ...
    # We skip `chunks=` (dask) on purpose: dask isn't installed in the env,
    # and it's unnecessary here -- GDAL's warper reads only the source pixels
    # needed for each reprojection through the VRT/windowed I/O, even with
    # a non-dask DataArray. The full raster is never materialized in RAM.
    # -----------------------------------------------------------------------
    src = rioxarray.open_rasterio(tif_path, masked=False)
    src = src.squeeze("band", drop=True)
    print(f"SMOD source CRS  : {src.rio.crs}")
    print(f"SMOD source shape: {src.shape}  (y, x)")
    print(f"SMOD nodata      : {src.rio.nodata}")

    # -----------------------------------------------------------------------
    # 3) Build the CRCM6 target grid as an empty DataArray carrying the
    #    rotated-pole CRS. We will reproject onto this grid using
    #    `reproject_match`, which inherits the target's CRS + affine
    #    transform + shape.
    # -----------------------------------------------------------------------
    ref = xr.open_dataset(CRCM6_REF_NC)

    # Rotated-pole CF attributes carried by the `rotated_pole` variable.
    # pyproj knows how to build the corresponding CRS directly from CF attrs.
    gm_attrs = dict(ref["rotated_pole"].attrs)
    print(f"CRCM6 grid_mapping : {gm_attrs}")
    crcm6_crs = CRS.from_cf(gm_attrs)
    print(f"CRCM6 CRS (PROJ)   : {crcm6_crs.to_proj4()}")

    rlat = ref["rlat"].values   # 1D, 655 points, step ~0.11 deg in rotated space
    rlon = ref["rlon"].values   # 1D, 655 points

    # IMPORTANT naming conventions for rioxarray:
    #   - spatial dims must be named "x" and "y" (or we must tell it explicitly)
    #   - "y" must be DECREASING for a north-up raster (affine convention);
    #     CRCM6 rlat is increasing (south -> north), so we'll flip it after.
    # To keep things simple and CF-correct, we build the target with dims
    # (rlat, rlon) and declare the spatial dims explicitly via
    # .rio.set_spatial_dims(x="rlon", y="rlat"), then write the CRS. We use
    # `inplace=False`-style methods (the default) and chain them.
    target = xr.DataArray(
        np.zeros((len(rlat), len(rlon)), dtype=np.float32),
        dims=("rlat", "rlon"),
        coords={"rlat": rlat, "rlon": rlon},
        name="target_grid",
    )
    target = (
        target
        .rio.set_spatial_dims(x_dim="rlon", y_dim="rlat", inplace=False)
        .rio.write_crs(crcm6_crs, inplace=False)
    )

    # -----------------------------------------------------------------------
    # 4) For each DEGURBA class: build a binary field, reproject with
    #    `Resampling.average`, store the result.
    #
    # Why `Resampling.average` on a 0/1 source = fraction of coverage:
    # with equal-area source pixels (Mollweide 1 km x 1 km), averaging the
    # source pixels that fall inside a target cell yields
    #     (# pixels == class C) / (# pixels covered)
    # which is the area fraction in that target cell. Exact for binary input.
    # -----------------------------------------------------------------------
    out_vars = {}

    for cls in DEGURBA_CLASSES:
        print(f"  Regridding class {cls} ...")

        # Build a binary float32 array (1 where source equals class, else 0).
        # We use float32 so that `average` has something to average; ints
        # would give surprising results with integer-averaging in GDAL.
        binary = xr.where(src == cls, np.float32(1.0), np.float32(0.0))

        # The binary DataArray inherits the source x/y coords but NOT the
        # CRS/transform machinery (xr.where strips .rio metadata). Reattach.
        binary = (
            binary
            .rio.write_crs(src.rio.crs, inplace=False)
            .rio.write_nodata(np.nan, inplace=False)   # NaN = "no source coverage here"
        )

        # Reproject onto the CRCM6 rotated-pole grid (same CRS + affine as
        # `target`). `reproject_match` is the one-call API that does the
        # warp under the hood with GDAL; it respects `Resampling.average`.
        frac = binary.rio.reproject_match(
            target,
            resampling=Resampling.average,
        )

        # Strip rio-added coords we don't need (e.g. `spatial_ref`) and
        # force dims naming back to (rlat, rlon).
        frac = frac.rename({"x": "rlon", "y": "rlat"})
        frac = frac.astype(np.float32)
        frac.attrs = {
            "long_name": f"Fraction of grid cell covered by DEGURBA class {cls}",
            "units": "1",
            "valid_min": 0.0,
            "valid_max": 1.0,
            "degurba_class_code": cls,
        }
        out_vars[f"frac_class{cls}"] = frac

    # -----------------------------------------------------------------------
    # 5) Derive Level-1 grouped fractions (pure linear combinations)
    # -----------------------------------------------------------------------
    for group_name, class_list in L1_GROUPS.items():
        summed = sum(out_vars[f"frac_class{c}"] for c in class_list)
        summed.attrs = {
            "long_name": f"Fraction of grid cell covered by DEGURBA {group_name}",
            "units": "1",
            "valid_min": 0.0,
            "valid_max": 1.0,
            "degurba_classes_included": ",".join(str(c) for c in class_list),
        }
        out_vars[f"frac_{group_name}"] = summed

    # -----------------------------------------------------------------------
    # 6) Assemble a Dataset and save as NetCDF alongside the input data
    # -----------------------------------------------------------------------
    ds_out = xr.Dataset(out_vars)
    ds_out = ds_out.assign_coords(rlat=("rlat", rlat), rlon=("rlon", rlon))

    # Carry the rotated_pole grid mapping variable so downstream xarray
    # readers can re-derive geographic lat/lon if needed. We replicate the
    # exact attrs of the source CRCM6 file.
    ds_out["rotated_pole"] = xr.DataArray(np.array(0, dtype=np.int32))
    ds_out["rotated_pole"].attrs = gm_attrs
    for name in out_vars:
        ds_out[name].attrs["grid_mapping"] = "rotated_pole"

    ds_out.attrs = {
        "title": "GHS-SMOD E2025 regridded onto CRCM6 rotated-pole grid",
        "source_dataset": ARCHIVE_STEM,
        "source_reference": "European Commission, Joint Research Centre (JRC), "
                            "GHS-SMOD R2023A V2.0, 1 km Mollweide (EPSG:54009)",
        "target_reference": "CRCM6 rotated-pole grid (same as "
                            "all UBB/UBD/UBE/UBF/UBG/UBH/UBI simulations)",
        "regridding_method": "GDAL average resampling on binary per-class fields "
                             "-- equivalent to area-weighted conservative remapping "
                             "because source pixels are equal-area (Mollweide 1 km).",
        "output_units": "fraction of grid cell (0 to 1) covered by the given "
                        "DEGURBA class or Level-1 group",
    }

    out_path = os.path.join(MASK_DIR, f"{ARCHIVE_STEM}_CRCM6grid.nc")
    # Use zlib compression to keep the file compact (8 variables x 655x655 ~ 3.4 MB raw)
    encoding = {v: {"zlib": True, "complevel": 4} for v in ds_out.data_vars
                if ds_out[v].ndim == 2}
    ds_out.to_netcdf(out_path, encoding=encoding)
    print(f"\nSaved: {out_path}")
    print(ds_out)


if __name__ == "__main__":
    main()
