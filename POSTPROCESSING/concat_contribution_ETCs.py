import xarray as xr
import pickle
import sys
import time
import argparse

def build_add_file(sim, wetdays, future):
    s = ''
    if wetdays:
        s += '_wetdays'
    if future and sim in ['UBG', 'UBH', 'UBI']:
        s += '_future_percentile'
    return s

def load_and_merge_all_pkl(wetdays, future):
    
    add_file = ''
    if wetdays:
        add_file += '_wetdays'
    if future:
        add_file += '_future_percentile'

    simulations = ['ERA5', 'UBB', 'UBD', 'UBE', 'UBF', 'UBG', 'UBH', 'UBI']
    variables = ['pr', 'ws']
    data = {}
    merged_all = {}
    output_file = f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/ALL/CONTRIB/contribution_ETCs_1000hPa{add_file}.pkl'

    for sim in simulations:
        for var in variables:
            add_file = build_add_file(sim, wetdays, future)
            file_path = f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/ALL/CONTRIB/contribution_ETCs_1000hPa_{sim}_{var}{add_file}.pkl'
            with open(file_path, 'rb') as file:
                data_key = f"{var}_{sim}"
                data[data_key] = pickle.load(file)

    for key in data[f"{variables[0]}_{simulations[0]}"].keys():
        merged_all[key] = {}
        for sim in simulations:
            arrs = []
            for var in variables:
                arr = data[f"{var}_{sim}"][key].rename(key).expand_dims(variable=[var])
                arrs.append(arr)
            merged_all[key][sim] = xr.concat(arrs, dim='variable')

    with open(output_file, 'wb') as f:
        pickle.dump(merged_all, f)

    print(f'Merged data saved to {output_file}')


def calcul_contribution(sim, variables, add_file):
        
        start_time = time.time()

        print(f'Processing simulation: {sim}')

        if sim in ['ERA5', 'UBB', 'UBD', 'UBE', 'UBF']:
            start_year = 1980
            # end_year = 2004
            end_year = 2014
        else:
            # start_year = 2058
            # end_year = 2082
            start_year = 2063
            end_year = 2097

        for var in variables:

            if var == 'pr':
                name_var = 'pr'
                folder_var = 'PR'
                file_var = 'pr'
            elif var == 'ws':
                name_var = 'surf_wind'
                if sim == 'ERA5':
                    folder_var = 'WIND/Magnitude'
                else:
                    folder_var = 'WIND'
                file_var = 'wind10'

            files = [f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{folder_var}/1000km_storm/total_{file_var}_{sim.lower()}_1000hPa_{season}_{iyear}.nc'
            for iyear in range(start_year, end_year + 1) for season in ['DJF', 'MAM', 'JJA', 'SON']]
            total = xr.open_mfdataset(files)
            total_seasonal = total[name_var].groupby('season').sum(dim='year', skipna=True)
            total_total = total[name_var].sum(dim=['year', 'season'], skipna=True)

            files = [f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{folder_var}/1000km_storm/count_{file_var}_{sim.lower()}_1000hPa_{season}_{iyear}.nc'
            for iyear in range(start_year, end_year + 1) for season in ['DJF', 'MAM', 'JJA', 'SON']]
            count = xr.open_mfdataset(files)
            count_seasonal = count[name_var].groupby('season').sum(dim='year', skipna=True)
            count_total = count[name_var].sum(dim=['year', 'season'], skipna=True)

            files = [f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{folder_var}/1000km_storm/total_{file_var}_ext_{sim.lower()}_1000hPa_{season}_{iyear}{add_file}.nc'
            for iyear in range(start_year, end_year + 1) for season in ['DJF', 'MAM', 'JJA', 'SON']]
            total_ext = xr.open_mfdataset(files)
            total_ext_seasonal = total_ext[name_var].groupby('season').sum(dim='year', skipna=True)
            total_ext_total = total_ext[name_var].sum(dim=['year', 'season'], skipna=True)

            files = [f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{folder_var}/1000km_storm/count_{file_var}_ext_{sim.lower()}_1000hPa_{season}_{iyear}{add_file}.nc'
            for iyear in range(start_year, end_year + 1) for season in ['DJF', 'MAM', 'JJA', 'SON']]
            count_ext = xr.open_mfdataset(files)
            count_ext_seasonal = count_ext[name_var].groupby('season').sum(dim='year', skipna=True)
            count_ext_total = count_ext[name_var].sum(dim=['year', 'season'], skipna=True)

            files = [f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{folder_var}/1000km_storm/total_{file_var}_{sim.lower()}_1000hPa_1000km_storm_{season}_{iyear}.nc' 
            for iyear in range(start_year, end_year + 1) for season in ['DJF', 'MAM', 'JJA', 'SON']]
            total_ETCs = xr.open_mfdataset(files)
            total_ETCs_seasonal = total_ETCs[name_var].groupby('season').sum(dim='year', skipna=True)
            total_ETCs_total = total_ETCs[name_var].sum(dim=['year', 'season'], skipna=True)

            files = [f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{folder_var}/1000km_storm/count_{file_var}_{sim.lower()}_1000hPa_1000km_storm_{season}_{iyear}.nc'
            for iyear in range(start_year, end_year + 1) for season in ['DJF', 'MAM', 'JJA', 'SON']]
            count_ETCs = xr.open_mfdataset(files)
            count_ETCs_seasonal = count_ETCs[name_var].groupby('season').sum(dim='year', skipna=True)
            count_ETCs_total = count_ETCs[name_var].sum(dim=['year', 'season'], skipna=True)

            files = [f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{folder_var}/1000km_storm/total_{file_var}_ext_{sim.lower()}_1000hPa_1000km_extreme_storm_{season}_{iyear}{add_file}.nc'
            for iyear in range(start_year, end_year + 1) for season in ['DJF', 'MAM', 'JJA', 'SON']]
            total_ext_EETCs = xr.open_mfdataset(files)
            total_ext_EETCs_seasonal = total_ext_EETCs[name_var].groupby('season').sum(dim='year', skipna=True)
            total_ext_EETCs_total = total_ext_EETCs[name_var].sum(dim=['year', 'season'], skipna=True)

            files = [f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/{folder_var}/1000km_storm/count_{file_var}_ext_{sim.lower()}_1000hPa_1000km_extreme_storm_{season}_{iyear}{add_file}.nc'
            for iyear in range(start_year, end_year + 1) for season in ['DJF', 'MAM', 'JJA', 'SON']]
            count_ext_EETCs = xr.open_mfdataset(files)
            count_ext_EETCs_seasonal = count_ext_EETCs[name_var].groupby('season').sum(dim='year', skipna=True)
            count_ext_EETCs_total = count_ext_EETCs[name_var].sum(dim=['year', 'season'], skipna=True)
        
            data_to_save = {
                'total_total': total_total.rename("total_total").compute(),
                'total_seasonal': total_seasonal.rename("total_seasonal").compute(),
                'count_total': count_total.rename("count_total").compute(),
                'count_seasonal': count_seasonal.rename("count_seasonal").compute(),
                'total_ext_seasonal': total_ext_seasonal.rename("total_ext_seasonal").compute(),
                'total_ext_total': total_ext_total.rename("total_ext_total").compute(),
                'count_ext_seasonal': count_ext_seasonal.rename("count_ext_seasonal").compute(),
                'count_ext_total': count_ext_total.rename("count_ext_total").compute(),
                'total_ETCs_seasonal': total_ETCs_seasonal.rename("total_ETCs_seasonal").compute(),
                'total_ETCs_total': total_ETCs_total.rename("total_ETCs_total").compute(),
                'count_ETCs_seasonal': count_ETCs_seasonal.rename("count_ETCs_seasonal").compute(),
                'count_ETCs_total': count_ETCs_total.rename("count_ETCs_total").compute(),
                'total_ext_EETCs_seasonal': total_ext_EETCs_seasonal.rename("total_ext_EETCs_seasonal").compute(),
                'total_ext_EETCs_total': total_ext_EETCs_total.rename("total_ext_EETCs_total").compute(),
                'count_ext_EETCs_seasonal': count_ext_EETCs_seasonal.rename("count_ext_EETCs_seasonal").compute(),
                'count_ext_EETCs_total': count_ext_EETCs_total.rename("count_ext_EETCs_total").compute(),
            }
            
            output_file = f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/ALL/CONTRIB/contribution_ETCs_1000hPa_{sim}_{var}{add_file}.pkl'
            with open(output_file, 'wb') as f:
                pickle.dump(data_to_save, f)

            end_time = time.time()
            print(f'{sim} {var} done and saved to {output_file} in {end_time - start_time:.2f} seconds')



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Calculate contribution of ETCs and EETCs to total precipitation and wind and merge in a single file.')
    parser.add_argument('--sim', type=str, required=False, help='Name of the simulation')
    parser.add_argument('--wetdays', action='store_true', help='Computation done with percentile calculated on wet days only for precipitation')
    parser.add_argument('--future', action='store_true', help='Computation done with percentile calculated on future period for future simulations')
    parser.add_argument('--original_selection', action='store_true', help='Use original selection criteria, with percentiles calculated on the full historical period')
    parser.add_argument('--only-calc', action='store_true', help='Run only calcul_contribution (no merge)')
    parser.add_argument('--only-merge', action='store_true', help='Run only load_and_merge_all_pkl (skip calculations)')

    # simulations = ['ERA5', 'UBB', 'UBD', 'UBE', 'UBF', 'UBG', 'UBH', 'UBI']
    variables = ['pr', 'ws']

    args = parser.parse_args()
    sim = args.sim
    wetdays = args.wetdays
    future = args.future
    original_selection = args.original_selection
    only_calc = args.only_calc
    only_merge = args.only_merge

    add_file = ''
    if original_selection and (wetdays or future):
        raise ValueError("original_selection cannot be combined with wetdays or future")
    
    add_file = build_add_file(sim, wetdays, future)

    if not only_merge:
        sys.stdout = open(f"/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/concat_contribution_ETCs_{sim}.txt", "w")
        calcul_contribution(sim, variables, add_file)

    if not only_calc:
        sys.stdout = open("/home/vdemeyer/TRACKING/KATJA/JOBS/OUTPUTS/concat_contribution_ETCs.txt", "w")
        load_and_merge_all_pkl(wetdays, future)

    sys.stdout.close()

# python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/concat_contribution_ETCs.py UBI --future --only-calc
# python /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/concat_contribution_ETCs.py --future --only-merge