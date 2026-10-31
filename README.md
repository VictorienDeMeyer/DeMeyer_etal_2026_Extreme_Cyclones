# DeMeyer_etal_2026_Extreme_Cyclones
Study of North American Extreme Extratropical Cyclones.

## Description
The project aims to track extratropical cyclones from regional simulations and ERA5 reanalysis over North America, to identify the most intense extratropical cyclones based on objective metrics related to the associated precipitation and surface winds, and further study the performance of models to replicate ERA5 as well as future changes.

## Usage
The project steps are divided as follows:

### Pre-processing
- Transfer of precipitation data, surface meridional wind, surface zonal wind, 850hPa relative vorticity, and mean sea level pressure to the Calcul Canada servers (`/PREPROCESSING/transfert_files_globus.sh`).
- Creation of a mask to restrict ERA5 data to the CRCM6 grid and create a buffer of 200km around the domain for the storm tracking algorithm (`/PREPROCESSING/create_mask_CRCM6_for_ERA5.ipynb`).
- Smoothing of relative vorticity and/or mean sea level pressure fields (`/PREPROCESSING/preprocess_year.py` or `create_storm_fields.sh` (not on GitHub) depending on whether the file is NetCDF or RPN, respectively).
- Calculation of surface wind magnitude (`/PREPROCESSING/Calculate_Wind_Magnitude.py` or `/PREPROCESSING/Calculate_Wind_Magnitude.sh` depending on whether Python or cdo works better, respectively).
- Calculation of wind and precipitation percentiles (`/PREPROCESSING/Calculate_Percentile.py`).
- Adding the missing timestep on 2015-01-01:T00:00:00.00000 on surface wind for the future simulations (UBG, UBH and UBI) (`/PREPROCESSING/interpolate_missing_data_2015.py`).
<!-- - For CRCM6 only: combine the smoothed mean sea level pressure yearly NetCDF files into decadal files (`slice_decade_preprocess.py`). -->

### Tracking
- Running the tracking of extratropical cyclones year by year (`/JOBS/GLOST/make_tracks.sh`).

### Cyclone phase classification (tropical / transition / extratropical)
The tracking algorithm detects every low-pressure system, including tropical cyclones. Each time step of each tracked cyclone is therefore labelled `TC`, `TRANSITION` or `ETC` with the cyclone phase space (CPS) of Hart (2003), i.e. from its thermal structure (warm or cold core, thermal symmetry):
- Calculation of the CPS parameters B (900-600 hPa thickness asymmetry), -VTL (fitted on 900, 850, 800, 700 and 600 hPa) and -VTU (fitted on 600, 500 and 300 hPa, as the CRCM6 files have no 400 hPa level) within 500 km of each 6-hourly track point (`/POSTPROCESSING/cyclone_phase_space.py`, `/JOBS/submit_jobs_cyclone_phase_space.sh`). Run it after `connect_ETCs.py`. For ERA5, which has the 400 hPa level, -VTU is also computed with the real and with an interpolated 400 hPa level as a control, and `classify_cyclone_phase.py` reports how the labels change with them.
- 24-h running mean of the parameters and labelling of every hourly track point (`/POSTPROCESSING/classify_cyclone_phase.py`, `/JOBS/submit_classify_cyclone_phase.sh`). A tropical phase is a deep (-VTL > 0 and -VTU > 0), symmetric (B < 10 m) warm core lasting at least 24 h equatorward of 40°N, a limit that removes the deep warm cores of mature high-latitude cyclones; the shallow warm core of warm-seclusion extratropical cyclones (-VTL > 0, -VTU < 0) is not tropical. Extratropical transition starts when the cyclone becomes asymmetric (B >= 10 m) or cold core (-VTL < 0) and is complete when both conditions are met (Evans and Hart 2003; Bieli et al. 2019; Garin et al. 2025). The output `{sim}_psl_smooth_400km_24h_1000hPa_phase.txt` contains the track, the smoothed parameters, the `phase` label and a `tc_storm` flag (storm with a tropical phase at any time).
- Evaluation of the labels of ERA5 and UBB (driven by ERA5) against the IBTrACS best tracks (`/POSTPROCESSING/validate_phase_ibtracs.py`; the North Atlantic and eastern North Pacific IBTrACS csv files must be downloaded into `ALL/IBTRACS`).
- Sanity checks of the diagnostics on synthetic fields: `python /TESTS/test_cyclone_phase.py` (a few seconds).

Required input: geopotential height at 900, 850, 800, 700, 600, 500 and 300 hPa (400 hPa optional, used for the control only), at 00, 06, 12 and 18 UTC, over 1980-2014 (ERA5, UBB, UBD, UBE, UBF) and 2063-2097 (UBG, UBH, UBI), stored as `{sim}/ZG/zg_{sim}_{YYYYMM}_se.nc` (variable `zg(time, plev, rlat, rlon)`, CRCM6 grid) and `ERA5/ZG/{YYYY}/{MM}/*.nc4` (variable `z`).

The tropical cyclones are then excluded from the post-processing below with the `--tc_filter` option of `ETCs_1000km.py`, `storm_percentile_metrics.py`, `contribution_ETCs.py`, `concat_contribution_ETCs.py` and `calculate_kde.py` (`TC_FILTER` environment variable in the job scripts, `tc_filter` in `aggregate_storm_percentile_metrics.ipynb`, `ETC_tools.open_df(sim, tc_filter=...)` in Python):
- `phase` (output tag `_noTC`): only the time steps labelled `ETC` are kept; the extratropical stage of a former tropical cyclone is kept.
- `storm` (output tag `_noTCstorm`): every cyclone with a tropical phase is removed.

In `ETCs_1000km.py`, each grid point is still attributed to the closest cyclone among all tracked cyclones, and is discarded if that cyclone is not extratropical, so that the precipitation and wind of a tropical cyclone are never attributed to a more distant extratropical cyclone. Without `--tc_filter`, all scripts behave and name their outputs exactly as before.

Example: `sbatch --export=ALL,TC_FILTER=phase /home/vdemeyer/TRACKING/KATJA/JOBS/submit_jobs_ETCs_1000km.sh`, then the same `TC_FILTER` for the metrics, contribution and density jobs.

### Post-processing
- Connecting extratropical cyclones from each file into a single text file covering the entire period (`/POSTPROCESSING/connect_ETCs.py`).
- Calculation of extratropical cyclones track density (`/POSTPROCESSING/calculate_kde.py`).
- Merging all track density files into a single NetCDF file (`/POSTPROCESSING/merge_density_all_sims_seasons.ipynb`).
- Creation of NetCDF masks within a 1000 km radius around each extratropical cyclone (`/POSTPROCESSING/ETCs_1000km.py`).
- Regridding of the GHS-SMOD DEGURBA raster onto the CRCM6 rotated-pole grid to produce per-class fraction-of-coverage fields used as the urban mask (`/POSTPROCESSING/degurba_regrid_to_crcm6.py`).
- Calculation of extreme metrics associated to individual extratropical cyclones over urban areas (`/POSTPROCESSING/storm_percentile_metrics.py`).
- Merging all individual files of extreme metrics of individual extratropical cyclones over urban areas in a single pickle file (`/POSTPROCESSING/aggregate_storm_percentile_metrics.ipynb`).
- Calculation of the contribution of precipitation and surface wind associated with extratropical cyclones year by year (`/POSTPROCESSING/contribution_ETCs.py`).
- Calculation of extratropical cyclones contribution over the entire period and concatenation in a single pickle file (`/POSTPROCESSING/concat_contributions_ETCs.py`).
- Regridding of each DataArray within the single pickle file over the ERA5 grid (`/POSTPROCESSING/regrid_over_ERA5_grid.ipynb`).

### Supplementary: Selection of storms for the ARRIME project
- Calculation of metrics for each extratropical cyclone year by year (`/POSTPROCESSING/ARRIME/EETCs_stat.py`).
- Merging all yearly pickle files into a single pickle file covering the entire period (`/POSTPROCESSING/ARRIME/append_pickle_EETCs_stat.ipynb`).
- Selection of the extratropical cyclones in order to run 2.5km simulations from CRCM6-GEM5 (`/POSTPROCESSING/ARRIME/EETCs_selection_for_2p5_sim.py`).

### Plotting
Numerous scripts are available at ./PLOT to plot the distribution of extreme extratropical cyclones according to the metric, contribution maps of extratropical cyclones, cyclone density, exceedance maps of different variables for certain extratropical cyclones, etc.

## Authors
Dr. Victorien De Meyer  
Postdoc  
UQAM
