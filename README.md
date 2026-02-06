## DeMeyer_etal_2026_Extreme_Cyclones
Study of North American Extreme Extratropical Cyclones.

## Description
The project aims to track extratropical cyclones from regional simulations and ERA5 reanalysis over North America, to identify the most intense extratropical cyclones based on objective metrics related to the associated precipitation and surface winds, and further study the performance of models to replicate ERA5 as well as future changes.

## Usage
The project steps are divided as follows:

## Pre-processing
- Transfer of precipitation data, surface meridional wind, surface zonal wind, 850hPa relative vorticity, and mean sea level pressure to the Calcul Canada servers.
- Creation of a mask to restrict ERA5 data to the CRCM6 grid and create a buffer of 200km around the domain for the storm tracking algorithm (`create_mask_CRCM6_for_ERA5.ipynb`).
- Smoothing of relative vorticity and/or mean sea level pressure fields (`preprocess_year.py` or `create_storm_fields.sh` depending on whether the file is NetCDF or RPN, respectively).
- For CRCM6 only: combine the smoothed mean sea level pressure yearly NetCDF files into decadal files (`slice_decade_preprocess.py`).

## Tracking
- Launching the tracking of extratropical cyclones by decade (`make_tracks_ERA5.sh` or `make_tracks_CRCM6.sh` depending on the input data).

## Post-processing
- Calculation of surface wind magnitude (`Calculate_Wind_Magnitude.py` or `Calculate_Wind_Magnitude.sh` depending on whether Python or cdo works better, respectively).
- Calculation of wind and precipitation percentiles (`Calculate_Percentile.py`).
- Adding the missing timestep on 2015-01-01:T00:00:00.00000 on surface wind for the future simulations (UBG, UBH and UBI) (`interpolate_missing_data_2015.py`).
- Connecting extratropical cyclones from each file into a single text file covering the entire period (`Connect_ETC.py`).
- Calculation of extratropical cyclones track density (`calculate_kde.py`).
- Calculation of metrics for each extratropical cyclone year by year (`EETCs_stat.py`).
- Merging all yearly pickle files into a single pickle file covering the entire period (`append_pickle_EETCs_stat.ipynb`).
- Selection of the extratropical cyclones in order to run 2.5km simulations from CRCM6-GEM5 (`EETCs_selection_for_2p5_sim.py`)
- Creation of NetCDF files for precipitation and surface wind associated only with extratropical cyclones (`ETCs_1000km.py`).
- Calculation of the contribution of precipitation and surface wind associated with extratropical cyclones year by year (`contribution_ETCs.py`).
- Calculation of extratropical cyclones contribution over the entire period and concatenation in a single pickle file (`concat_contributions_ETCs.py`).
- Regridding of each DataArray within the single pickle file over the ERA5 grid (`regrid_over_ERA5_grid.ipynb`).

## Plotting
Numerous scripts are available at ./PLOT to plot the distribution of extreme extratropical cyclones according to the metric, contribution maps of extratropical cyclones, cyclone density, exceedance maps of different variables for certain extratropical cyclones, etc.

## Authors
Dr. Victorien De Meyer  
Postdoc  
UQAM
