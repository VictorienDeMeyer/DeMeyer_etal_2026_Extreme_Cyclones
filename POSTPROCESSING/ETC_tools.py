import pandas as pd
import numpy as np
import pickle
import xarray as xr

_FILE_PREFIX = '/home/vdemeyer/projects/rrg-gachon/vdemeyer/'

# Filename tags of the outputs produced with a tropical-cyclone filter (see open_df).
# The empty tag (no filter) keeps every legacy filename unchanged.
TC_FILTER_TAGS = {None: '', 'phase': '_noTC', 'storm': '_noTCstorm'}


def tc_filter_tag(tc_filter):
    """
    Return the filename tag associated with a tropical-cyclone filter.

    :param tc_filter: None, 'phase' or 'storm' (see open_df).
    :return: '' for None, '_noTC' for 'phase', '_noTCstorm' for 'storm'.
    """
    if tc_filter not in TC_FILTER_TAGS:
        raise ValueError(f"tc_filter must be one of {list(TC_FILTER_TAGS)}, got {tc_filter!r}")
    return TC_FILTER_TAGS[tc_filter]


def track_file(sim):
    """Connected track file of a simulation (output of connect_ETCs.py)."""
    return f'{_FILE_PREFIX}{sim}/STORM_RELATED/TRACK/{sim}_psl_smooth_400km_24h_1000hPa.txt'


def phase_file(sim):
    """Track file with the cyclone phase labels (output of classify_cyclone_phase.py)."""
    return f'{_FILE_PREFIX}{sim}/STORM_RELATED/TRACK/{sim}_psl_smooth_400km_24h_1000hPa_phase.txt'


def _valid_storms(df, sim):
    storm_bounds = df.groupby('storm')['date'].agg(['min', 'max'])
    if sim in ['UBG', 'UBH', 'UBI']:
        return storm_bounds.query('min.dt.year >= 2063 and max.dt.year <= 2097').index
    return storm_bounds.query('min.dt.year >= 1980 and max.dt.year <= 2014').index


def open_df(sim, period_filtering=True, tc_filter=None, keep_non_etc=False):
    """
    Load the storm tracking DataFrame.

    :param sim: Simulation name (e.g., 'UBB', 'ERA5').
    :param period_filtering: Boolean indicating if we keep only storms within a 35 years frame.
    :param tc_filter: Tropical-cyclone filter based on the cyclone phase space labels
        written by classify_cyclone_phase.py:
          - None    : all tracked cyclones (original behaviour, original track file).
          - 'phase' : keep only the time steps labelled 'ETC'. Tropical ('TC') and
                      transition ('TRANSITION') time steps are removed, but the
                      extratropical stage of a former tropical cyclone is kept.
          - 'storm' : remove every cyclone that has a tropical phase at any time.
        Period filtering is applied on the full tracks, before the phase filter.
    :param keep_non_etc: Only used with tc_filter. If True, no time step is removed and a
        boolean column 'is_etc' flags the time steps kept by the filter.
    :return: DataFrame of storm data.
    """
    tc_filter_tag(tc_filter)

    if tc_filter is None:
        df = pd.read_csv(
            track_file(sim),
            sep=r' ',
            header=0,
            engine='python',
            names=['storm','point','i','j','date','lat','lon','pressure']
        )
    else:
        df = pd.read_csv(phase_file(sim), sep=' ', header=0)
    df['date'] = pd.to_datetime(df['date'])

    if period_filtering:
        df = df[df['storm'].isin(_valid_storms(df, sim))]

    if tc_filter is not None:
        if tc_filter == 'phase':
            is_etc = df['phase'] == 'ETC'
        else:
            is_etc = ~df['tc_storm'].astype(bool)
        if keep_non_etc:
            df = df.assign(is_etc=is_etc.values)
        else:
            df = df[is_etc]

    return df


def open_eetc(sim, metric='diff', wetdays=False, future=True, original_selection=False, period_filtering=True):
    """
    Load the EETC pickle dictionary.

    :param sim: Simulation name (e.g., 'UBB', 'ERA5').
    :param metric: Metric type ('ratio' or 'diff').
    :param wetdays: Boolean indicating if wetdays are considered for percentile calculation.
    :param future: Boolean indicating if percentiles are calculated on future period.
    :param original_selection: Boolean indicating if the original selection is used.
    :param period_filtering: Boolean indicating if we keep only storms within a 35 years frame.
    :return: EETC dictionary.
    """
    if original_selection and (wetdays or future or metric == 'ratio'):
        raise ValueError("original_selection cannot be combined with wetdays, future or ratio metric")
    if wetdays and future:
        raise ValueError("wetdays and future cannot be combined")

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
        f'{_FILE_PREFIX}{sim}/STORM_RELATED/EETC/EETC_cum_{sim}_Quebec_1000hPa_1979-{end_year}_compound_8hrs_quantile_SSI{add_file}'
    )

    print(f"Loading data from: {eet_dict_file} with {period_filtering} period filtering")

    with open(eet_dict_file, 'rb') as pickle_file:
        EETC_dict = pickle.load(pickle_file)

    if period_filtering:
        valid = _valid_storms(open_df(sim, period_filtering=False), sim)
        EETC_dict = {k: v for k, v in EETC_dict.items() if k in valid}

    return EETC_dict


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

    EETC_dict = open_eetc(sim, future=future)
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
