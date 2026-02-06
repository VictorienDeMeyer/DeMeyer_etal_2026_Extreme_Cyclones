import pandas as pd
import numpy as np
import pickle
import xarray as xr

def open_files(sim, metric='diff', wetdays=False, future=True, original_selection=False, period_filtering=True):
    """
    Open and load the necessary files based on the input parameters.

    :param sim: Simulation name (e.g., 'UBB', 'ERA5').
    :param metric: Metric type ('ratio' or 'diff').
    :param wetdays: Boolean indicating if wetdays are considered for percentile calculation.
    :param future: Boolean indicating if percentiles are calculated on future period.
    :param original_selection: Boolean indicating if the original selection is used.
    :param period_filtering: Boolean indicating if we keep only storms within a 35 years frame.
    :return: A tuple containing the DataFrame of storm data and the EETC dictionary.
    """
    
    if original_selection and (wetdays or future or metric=='ratio'):
        raise ValueError("original_selection cannot be combined with wetdays, future or ratio metric")
    if wetdays and future:
        raise ValueError("wetdays and future cannot be combined")
    
    file_prefix = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/'
        
    # Load storm tracking data   
    storm_data_file = f'{file_prefix}{sim}_psl_smooth_400km_12h_1005hPa.txt'
    df = pd.read_csv(
        storm_data_file,
        sep=r' ',
        header=0,
        engine='python',
        names=['storm','point','i','j','date','lat','lon','pressure']
    )
    df['date'] = pd.to_datetime(df['date'])

    #Load EETC pickle file
    if sim in ['UBB', 'ERA5']:
        end_year = 2023
    elif sim in ['UBG', 'UBH']:
        end_year = 2100
    elif sim == 'UBI':
        end_year = 2098
    else:
        end_year = 2014
    
    add_file = ''
    if not original_selection:
        if wetdays:
            add_file += '_wetdays'
        if future and sim in ['UBG', 'UBH', 'UBI']:
            add_file += '_future_percentile'
        add_file += f'_{metric}.pkl'

    eet_dict_file = (
        f'{file_prefix}EETC/EETC_cum_{sim}_Quebec_1005hPa_1979-{end_year}_compound_8hrs_quantile_SSI{add_file}'
    )

    print(f"Loading data from: {eet_dict_file} with {period_filtering} period filtering")
    
    with open(eet_dict_file, 'rb') as pickle_file:
        EETC_dict = pickle.load(pickle_file)

    if period_filtering:
        # Filter storms so we only keep those within the desired time period of 35 years
        storm_bounds = df.groupby('storm')['date'].agg(['min', 'max'])
        if sim in ['UBG', 'UBH', 'UBI']:
            # Conserver uniquement les storms dont la première date est >= 2058 et <= 2082
            valid_storms = storm_bounds.query('min.dt.year >= 2058 and max.dt.year <= 2082').index
            df = df[df['storm'].isin(valid_storms)]
            EETC_dict = {k: v for k, v in EETC_dict.items() if k in valid_storms}
        else:
            # Conserver uniquement les storms dont la première date est >= 1980 et <= 2004
            valid_storms = storm_bounds.query('min.dt.year >= 1980 and max.dt.year <= 2004').index
            df = df[df['storm'].isin(valid_storms)]
            EETC_dict = {k: v for k, v in EETC_dict.items() if k in valid_storms}

    return df, EETC_dict

def normalize_EETC_dict(EETC_dict, quantile):
    """
    Normalize the EETC dictionary for all metrics that are xarray DataArrays for a specific quantile.

    :param EETC_dict: Dictionary containing EETC data.
    :param quantile: The specific quantile to normalize the data for.
    :return: A normalized version of the EETC dictionary.
    """

    normalized_data = {}

    sample_key = next(iter(EETC_dict))
    all_metrics = EETC_dict[sample_key].keys()

    metrics_to_normalize = [m for m in all_metrics if isinstance(EETC_dict[sample_key][m], xr.DataArray)]

    for metric in metrics_to_normalize:
        values = [EETC_dict[key][metric].sel(quantile=quantile).item() for key in EETC_dict]
        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val if max_val != min_val else np.nan  # Avoid division by zero

        for key in EETC_dict:
            if key not in normalized_data:
                normalized_data[key] = {}

            if metric not in normalized_data[key]:
                normalized_data[key][metric] = xr.zeros_like(EETC_dict[key][metric])

            val = EETC_dict[key][metric].sel(quantile=quantile).item()
            norm_val = (val - min_val) / range_val

            normalized_data[key][metric].loc[dict(quantile=quantile)] = norm_val

    for key in EETC_dict:
        for metric in EETC_dict[key]:
            if metric not in metrics_to_normalize:
                if key not in normalized_data:
                    normalized_data[key] = {}
                normalized_data[key][metric] = EETC_dict[key][metric]

    return normalized_data

def calculate_ranking(sim, quantile, future=True):
    """
    Process output tracking data and postprocessed data to compute sorted ranks for different metrics for ETCs.
    For the product method, it is necessary to normalize the metrics as one should not multiply 2 metrics with different range of value
    :param sim: Simulation name.
    :param quantile: Quantile value.
    :param method: Ranking method ('borda' or 'product').
    :return: Sorted ranks for different metrics.
    """

    _, EETC_dict = open_files(sim, future)
    EETC_dict_norm = normalize_EETC_dict(EETC_dict, quantile)

    def compute_combined_scores(metric1, metric2):
        """Compute combined scores by multiplying two normalized metrics."""
        return {
            storm: metric1[storm].sel(quantile=quantile) * metric2[storm].sel(quantile=quantile)
            for storm in metric1 if storm in metric2 and not (
                metric1[storm].sel(quantile=quantile) == 0 and metric2[storm].sel(quantile=quantile) == 0
            )
        }     
    
    # Compute combined scores
    combined_scores = compute_combined_scores(
        {storm: EETC_dict_norm[storm]['cum_precip'] for storm in EETC_dict_norm},
        {storm: EETC_dict_norm[storm]['cum_wind'] for storm in EETC_dict_norm}
    )
    combined_avg_scores = compute_combined_scores(
        {storm: EETC_dict_norm[storm]['cum_avg_precip'] for storm in EETC_dict_norm},
        {storm: EETC_dict_norm[storm]['cum_avg_wind'] for storm in EETC_dict_norm}
    )
    combined_SSI_scores = compute_combined_scores(
        {storm: EETC_dict_norm[storm]['cum_precip'] for storm in EETC_dict_norm},
        {storm: EETC_dict_norm[storm]['SSI'] for storm in EETC_dict_norm}
    )
    combined_SSI_avg_scores = compute_combined_scores(
        {storm: EETC_dict_norm[storm]['cum_avg_precip'] for storm in EETC_dict_norm},
        {storm: EETC_dict_norm[storm]['SSI'] for storm in EETC_dict_norm}
    )

    # Sort storms based on combined scores
    sorted_EETC_cum_rank = sorted(combined_scores, key=combined_scores.get, reverse=True)
    sorted_EETC_cum_avg_rank = sorted(combined_avg_scores, key=combined_avg_scores.get, reverse=True)
    sorted_EETC_cum_SSI_rank = sorted(combined_SSI_scores, key=combined_SSI_scores.get, reverse=True)
    sorted_EETC_cum_avg_SSI_rank = sorted(combined_SSI_avg_scores, key=combined_SSI_avg_scores.get, reverse=True)        

    
    return (
        sorted_EETC_cum_rank,
        sorted_EETC_cum_avg_rank,
        sorted_EETC_cum_SSI_rank,
        sorted_EETC_cum_avg_SSI_rank,
        combined_scores,
        combined_avg_scores,
        combined_SSI_scores,
        combined_SSI_avg_scores,
        EETC_dict,
        EETC_dict_norm
    )