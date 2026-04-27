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
- Launching the tracking of extratropical cyclones by decade (`/JOBS/make_tracks_ERA5.sh` or `/JOBS/make_tracks_CRCM6.sh` depending on the input data).

### Post-processing
- Connecting extratropical cyclones from each file into a single text file covering the entire period (`/POSTPROCESSING/connect_ETCs.py`).
- Calculation of extratropical cyclones track density (`/POSTPROCESSING/calculate_kde.py`).
- Merging all track density files into a single NetCDF file (`/POSTPROCESSING/merge_density_all_sims_seasons.ipynb`).
- Creation of NetCDF masks within a 1000 km radius around each extratropical cyclone (`/POSTPROCESSING/ETCs_1000km.py`).
- Calculation of extreme metrics associated to individual extratropical cyclones (`/POSTPROCESSING/storm_percentile_metrics.py`).
- Merging all individual files of extreme metrics of individual extratropical cyclones in a single pickle file (`/POSTPROCESSING/aggregate_storm_percentile_metrics.py`).
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
