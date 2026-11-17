# DeMeyer_etal_2026_Extreme_Cyclones

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21922110.svg)](https://doi.org/10.5281/zenodo.21922110)

Analysis code of:

> De Meyer, V., Di Luca, A., and Chen, T.-C.: Future Projections of Extreme Wind and Precipitation Associated With Extratropical Cyclones Over North America using Regional Climate Simulations, EGUsphere [preprint], https://doi.org/10.5194/egusphere-2026-4825, 2026.

Extratropical cyclones (ETCs) are tracked in hourly ERA5 and CRCM6-GEM5 data over North America. The precipitation and near-surface wind exceedances above the 99th percentile of all hours, within 1000 km of an ETC centre, are then accumulated (`EE_cum|ETC`). This accumulation is decomposed into an intensity term, a threshold term and an occurrence term. With these diagnostics, the code:
- evaluates the historical simulations against ERA5, and against the IMERG satellite precipitation;
- separates the contributions of the regional model and of the driving data to the biases;
- tests the significance of the differences;
- attributes the projected changes, first over the whole domain and then for the most extreme individual ETCs over northeastern North America (NNA).

The repository contains everything needed to reproduce the results of the article. Releases are archived on Zenodo; the DOI above always points to the latest version:
- `v1.0.0-submitted`: code of the submitted (discussion) version;
- `v2.0.0-revised`: code of the revised version.

## Contents
- [Simulations and data](#simulations-and-data)
- [Software environment](#software-environment)
- [Repository structure](#repository-structure)
- [Workflow](#workflow)
- [Figures and tables of the article](#figures-and-tables-of-the-article)
- [Submitted and revised versions](#submitted-and-revised-versions)
- [Citation, license and authors](#citation-license-and-authors)

## Simulations and data

| Name in the code | Dataset | Periods |
|---|---|---|
| `ERA5` | ERA5 reanalysis | 1980–2014 |
| `UBB` | CRCM6-GEM5 driven by ERA5 | 1980–2014 |
| `UBD` / `UBG` | CRCM6-GEM5 driven by EC-Earth3-Veg | 1980–2014 / 2063–2097 (SSP3-7.0) |
| `UBE` / `UBH` | CRCM6-GEM5 driven by MPI-ESM1-2-HR | 1980–2014 / 2063–2097 (SSP3-7.0) |
| `UBF` / `UBI` | CRCM6-GEM5 driven by MIROC6 | 1980–2014 / 2063–2097 (SSP3-7.0) |
| `IMERG` | IMERG Final Run V07, half-hourly, 0.1° | 2001–2014 |

The CRCM6-GEM5 simulations cover the CORDEX North American domain (NAM-12, 0.11° rotated-pole grid).

**Inputs.** The input data are not distributed with this repository. They come from:
- **CRCM6-GEM5 (ESCER, UQAM):**
  - hourly precipitation, near-surface wind components and mean sea level pressure;
  - geopotential height at 900–300 hPa at 00, 06, 12 and 18 UTC;
  - land fraction and orography.
- **ERA5 (Copernicus Climate Data Store):**
  - hourly total precipitation, 10 m wind components and mean sea level pressure;
  - geopotential on pressure levels;
  - land-sea mask and surface geopotential.
- **IMERG V07B Final Run:** NASA GES DISC, https://doi.org/10.5067/GPM/IMERG/3B-HH/07.
- **IBTrACS v04r01:** North Atlantic and eastern North Pacific csv files.
- **Urban areas:** GHS-SMOD R2023A (E2025 epoch, 1 km) of the Global Human Settlement Layer.
- **Orography and land fraction of the driving AOGCMs:** CMIP6 `orog` and `sftlf` (table `fx`, historical), for the panels of the domain figure.
- **Map background:** Natural Earth 1:50m shaded relief (`NE1_50M_SR_W.tif`).

**Paths.** The locations of the input data and of the outputs are written at the top of each script and notebook. Adapt them to your own data before running the code.

## Software environment
The analysis was run on a SLURM cluster: the scripts in `JOBS/` are SLURM job scripts. Main Python packages and the versions used for the article:

| Package | Version | Package | Version |
|---|---|---|---|
| Python | 3.11.5 | xesmf / esmpy | 0.8.8 / 8.8.0 |
| numpy | 1.26.4 | cartopy | 0.22.0 |
| pandas | 2.2.2 | matplotlib | 3.8.4 |
| xarray | 2025.1.2 | cmocean / cmcrameri | 3.0.3 / 1.8 |
| scipy | 1.12.0 | scikit-learn | 1.5.2 |
| dask / dask-image | 2025.1.0 / 2021.12.0 | netCDF4 / zarr | 1.7.2 / 2.18.3 |
| jupyterlab / nbconvert | 4.3.5 / 7.16.4 | tqdm / braceexpand | 4.66.4 / 0.1.7 |

`POSTPROCESSING/degurba_regrid_to_crcm6.py` also needs `rioxarray` and `rasterio`. The ERA5 wind magnitude is computed with `cdo`.

The tracking algorithm is a Fortran program. It needs `gfortran` and the netCDF-Fortran library, and is compiled with:

```bash
make tracks        # builds storm_tracks.Abs from storm_tracks.f90 and its modules
```

## Repository structure

```
storm_tracks.f90, *_mod.f90, input_args.cdk, Makefile   Fortran tracking algorithm
PREPROCESSING/    masks, smoothing of the pressure, wind magnitude, percentiles, IMERG files
POSTPROCESSING/   track connection, cyclone phase space, 1000 km attribution, accumulations,
                  densities, regridding, significance, storm metrics
PLOT/             figure notebooks and scripts
JOBS/             SLURM job scripts (JOBS/GLOST/ for the tracking)
```


## Workflow
The steps below are run in this order. Unless stated otherwise, each Python script has a SLURM job script in `JOBS/` that loops over the simulations and years.

**The tropical cyclone filter.** The revised article excludes the tropical cyclones. Every job of the chain is therefore submitted with `TC_FILTER=phase` (option `--tc_filter phase`; `tc_filter = 'phase'` at the top of the notebooks). The outputs then carry the tag `_noTC`.

### 1. Pre-processing (`PREPROCESSING/`)
- **ERA5 domain mask:** restricts ERA5 to the CRCM6-GEM5 domain, with a 200 km buffer for the tracking (`create_mask_CRCM6_for_ERA5.ipynb`).
- **Pressure smoothing:** the mean sea level pressure is smoothed with a 400 km filter (`preprocess_year.py`, `JOBS/submit_jobs_preprocess_year.sh`).
- **Wind magnitude:**
  - CRCM6-GEM5: `Calculate_Wind_Magnitude.py`, `JOBS/submit_Calculate_Wind_Magnitude.sh`;
  - ERA5: `JOBS/Calculate_Wind_Magnitude_cdo.sh` (cdo).
- **Missing time steps of the future simulations,** filled by linear interpolation in time:
  - 2015-01-01T00 of the surface wind (`interpolate_missing_data_2015.py`);
  - 2030-04-01T00 of UBI, only if it is missing (`interpolate_missing_data_UBI_2030.py`).
- **99th (and 98th, 99.5th, 99.9th) percentiles** of all hours of precipitation and wind, 1980–2014 (`Calculate_Percentile.py`, `JOBS/submit_Calculate_Percentile.sh`). The future periods use the percentile of their historical simulation.

### 2. Tracking (root folder, `JOBS/GLOST/`)
The algorithm tracks the minima of the smoothed pressure, year by year: `make_tracks.sh`, run through GLOST with `generate_tasks_glost_make_tracks.sh` then `submit_glost_job_make_tracks.sh`. The yearly track files are then connected into one file per simulation (`POSTPROCESSING/connect_ETCs.py`).

### 3. Exclusion of the tropical cyclones (`POSTPROCESSING/`)
Each time step of each tracked cyclone is labelled tropical (`TC`), transition (`TRANSITION`) or extratropical (`ETC`) with the cyclone phase space of Hart (2003):
- **CPS parameters:** thermal asymmetry B (900–600 hPa), −V<sub>T</sub><sup>L</sup> (900–600 hPa) and −V<sub>T</sub><sup>U</sup> (600–300 hPa; 400 hPa is not available in the CRCM6-GEM5 output), within 500 km of each 6-hourly track point (`cyclone_phase_space.py`, `JOBS/submit_jobs_cyclone_phase_space.sh`).
- **Labels:** 24 h running mean of the parameters and labelling of every hourly track point (`classify_cyclone_phase.py`). A tropical phase is a deep, symmetric warm core (−V<sub>T</sub><sup>L</sup> > 0, −V<sub>T</sub><sup>U</sup> > 0, B < 10 m) lasting at least 24 h equatorward of 40°N. The output `{sim}_psl_smooth_400km_24h_1000hPa_phase.txt` adds the `phase` label and a `tc_storm` flag (storm with a tropical phase at any time) to the tracks.
- **Validation of ERA5 and UBB against IBTrACS:** `validate_phase_ibtracs.py`. It is run with the labelling by `JOBS/submit_classify_cyclone_phase.sh`.

With the filter `phase`, only the time steps labelled `ETC` are kept, including the extratropical stage of former tropical cyclones. Grid points whose closest cyclone is tropical or in transition are discarded, so that the precipitation and wind of a tropical cyclone are never attributed to a more distant ETC.

### 4. Accumulated exceedances and track density (`POSTPROCESSING/`)
- **Storm IDs** within 1000 km of each ETC, every hour (`ETCs_1000km.py`, `JOBS/submit_jobs_ETCs_1000km.sh`).
- **Yearly and seasonal sums and counts of the exceedances** within 1000 km of an ETC (`contribution_ETCs.py`, `JOBS/submit_jobs_contribution_ETCs.sh`).
- **Merge over the periods,** one file for all the simulations (`concat_contribution_ETCs.py`, `JOBS/submit_jobs_concat_contribution_ETCs.sh`).
- **Track density** with a 200 km Gaussian kernel (`calculate_kde.py`, `JOBS/submit_jobs_calculate_kde.sh`), merged by `merge_density_all_sims_seasons.ipynb`. The yearly densities needed for the significance come from the mode `YEARLY` (see `JOBS/submit_significance_masks.sh`).
- **Regridding onto the ERA5 grid** (`regrid_over_ERA5_grid.ipynb`): conservative for the accumulations, nearest neighbour for the counts, bilinear for the percentiles and densities.

### 5. Significance (`POSTPROCESSING/significance_masks.py`, `JOBS/submit_significance_masks.sh`)
Each map is tested against interannual variability on the yearly values:
- **CRCM6-GEM5 driven by ERA5 against ERA5:** paired t-test on the yearly differences (same years);
- **AOGCM-driven simulations against ERA5, and projected changes:** Welch's t-test.

The false discovery rate is controlled at 0.10 over each map. The non-significant points are hatched on the maps.

### 6. Comparison with IMERG, 2001–2014
Each dataset is processed on its native grid. IMERG uses the ERA5 tracks and their tropical cyclone labels.
- **IMERG hourly files and domain mask:** `PREPROCESSING/preprocess_IMERG.py`, `JOBS/preprocess_IMERG.sh`.
- **Percentiles over 2001–2014:** `Calculate_Percentile.py --period 2001-2014`, with `--sim IMERG` for IMERG.
- **Storm IDs within 1000 km for IMERG:** `ETCs_1000km.py --sim IMERG --tc_filter phase`.
- **Accumulations over 2001–2014:** `PERIOD=2001-2014` in the contribution and merge jobs.
- **Regridding and significance:** paired t-test on the 14 yearly differences (`POSTPROCESSING/regrid_IMERG_evaluation.ipynb`).
- **Figures:** `PLOT/plot_map_IMERG_evaluation.ipynb`. Both notebooks are run by `JOBS/run_IMERG_evaluation.sh`.

### 7. Individual ETCs over northeastern North America (`POSTPROCESSING/`)
- **Exceedance metrics of each ETC** over the land grid cells of the NNA region (40–50°N, 90–60°W), for the 99th and 99.9th percentiles (`storm_percentile_metrics.py`). Submit with `sbatch --export=ALL,MASK=land,REGION=NNA2,TC_FILTER=phase JOBS/submit_jobs_storm_percentile_metrics.sh`.
- **Aggregation:** `aggregate_storm_percentile_metrics.ipynb`.
- **Urban mask** of the supplementary figure: `degurba_regrid_to_crcm6.py`.

### 8. Figures (`PLOT/`)
The notebooks are run in JupyterLab, with `tc_filter = 'phase'`. `PLOT/plot_map_ETCs_RCM_vs_driving.py` is run by `JOBS/plot_map_ETCs_RCM_vs_driving.sh`.

## Figures and tables of the article

**Main text**, in the order of the article:

| Content | Code | Figure file |
|---|---|---|
| Domain, orography of CRCM6-GEM5, ERA5 and the AOGCMs, NNA region | `plot_map_orography.ipynb` | `orography_domain.png` |
| ETC track density, ERA5 and biases | `plot_map_ETCs_diff_w_ERA5.ipynb` | `ETC_density_hist_noTC.png` |
| Accumulated precipitation exceedance of ERA5 | `plot_map_ETCs_diff_w_ERA5.ipynb` | `PR_hist_ERA5_noTC.png` |
| Precipitation biases and their decomposition | `plot_map_ETCs_diff_w_ERA5.ipynb` | `PR_hist_vs_ERA5_noTC.png` |
| Accumulated wind exceedance of ERA5 | `plot_map_ETCs_diff_w_ERA5.ipynb` | `WS_hist_ERA5_noTC.png` |
| Wind biases and their decomposition | `plot_map_ETCs_diff_w_ERA5.ipynb` | `WS_hist_vs_ERA5_noTC.png` |
| Contributions of the regional model and of the driving data (table) | `plot_map_ETCs_RCM_vs_driving.py` | `RCM_VS_DRIVING/rcm_vs_driving_bias_noTC.md` |
| ERA5 and CRCM6-GEM5 driven by ERA5 against IMERG | `plot_map_IMERG_evaluation.ipynb` | `IMERG/fig_PR_vs_IMERG_2001-2014.png` |
| Projected change of the track density | `plot_map_ETCs_diff_hist_w_future.ipynb` | `ETC_density_fut_vs_hist_noTC.png` |
| Projected change of the precipitation exceedance | `plot_map_ETCs_diff_hist_w_future.ipynb` | `PR_fut_vs_hist_noTC.png` |
| Projected change of the wind exceedance | `plot_map_ETCs_diff_hist_w_future.ipynb` | `WS_fut_vs_hist_noTC.png` |
| Top-10 seasonal ETCs over NNA: occurrence and intensity | `plot_storm_percentile_metrics_land_NNA2_seasonal.ipynb` | `scatter_top10_seasonal_storms_cumul_PR_NNA2_noTC.png` |
| Top-10 seasonal ETCs over NNA: ranked intensity | `plot_storm_percentile_metrics_land_NNA2_seasonal.ipynb` | `rankshaded_top10_seasonal_storms_intensity_PR_NNA2_noTC.png` |

The validation of the tropical cyclone labels against IBTrACS, given in the article, comes from `validate_phase_ibtracs.py`.

**Supplement:**

| Content | Code | Figure file |
|---|---|---|
| Urban areas and NNA region | `plot_degurba_thresholds.ipynb` | `supp_urban_mask_NNA2.png` |
| 99th and 99.9th percentiles of precipitation and wind | `plot_percentiles.ipynb` | `supp_p99_*_hist.png`, `supp_p999_*_hist.png` |
| Seasonal density and exceedance biases | `plot_map_ETCs_diff_w_ERA5.ipynb` | `supp_seasonal_*_hist*.png` |
| Decomposition terms of the biases | `plot_map_ETCs_diff_w_ERA5.ipynb` | `supp_terms_*_hist_noTC.png`, `supp_term1&2_*_hist_noTC.png` |
| Contributions of the regional model and of the driving data (maps) | `plot_map_ETCs_RCM_vs_driving.py` | `RCM_VS_DRIVING/{PR,WS}_bias_RCM_vs_driving_noTC.png` |
| Decomposition of the differences with IMERG | `plot_map_IMERG_evaluation.ipynb` | `IMERG/figS_terms_PR_vs_IMERG_2001-2014.png` |
| Seasonal projected changes and their terms | `plot_map_ETCs_diff_hist_w_future.ipynb` | `supp_seasonal_*_fut_vs_hist_noTC.png`, `supp_terms_*_fut_vs_hist_noTC.png` |
| Tracks of the top-10 ETCs and wind results over NNA | `plot_storm_percentile_metrics_land_NNA2_seasonal.ipynb` | `supp_tracks_top10_*_NNA2_noTC.png`, `*_WS_NNA2_noTC.png` |

## Submitted and revised versions
The revision added the following:
- the exclusion of the tropical cyclones (cyclone phase space, `TC_FILTER=phase`);
- the significance masks;
- the separation of the contributions of the regional model and of the driving data;
- the comparison with IMERG;
- the domain and orography figure.

Without `TC_FILTER`, or with `tc_filter = None` in the notebooks, the scripts keep all tracked cyclones and name their outputs as in the submitted version. The code of the submitted version is archived as `v1.0.0-submitted`.

**Not part of the article.** `POSTPROCESSING/ARRIME/` and the jobs `EETCs_stat.sh` and `EETCs_selection_for_2p5_sim.sh` select ETCs for 2.5 km simulations with CRCM6-GEM5 (ARRIME project).

## Citation, license and authors
Please cite the article and the archived code (`CITATION.cff`; Zenodo DOI above). The code is distributed under the MIT license (`LICENSE`).

- Victorien De Meyer: Centre ESCER, Université du Québec à Montréal, Canada (code)
- Alejandro Di Luca: Centre ESCER, Université du Québec à Montréal, Canada
- Ting-Chen Chen: Moody's, London, United Kingdom
