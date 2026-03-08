import xarray as xr
import argparse
import numpy as np

""""
Ce script permet de calculer la magnitude du vent à partir des composantes u et v du vent année par année.
Il permet de lancer autant de jobs que de simulations.
CDO fait ça mieux pour ERA5 (voir dans /JOBS/Calculate_Wind_Magnitude_cdo.sh) donc ce script est orienté pour les simulations du CRCMC6.

"""

def main(sim):

    print('\n\n', sim)

    if sim=='UBB':
        start_year = 1979
        end_year = 2023
    elif sim in ['UBD', 'UBE', 'UBF']:
        start_year = 1979
        end_year = 2014
    elif sim in ['UBG', 'UBH', 'UBI']:
        start_year = 2015
        end_year = 2100


    for year in range(start_year, end_year+1):
        print(year)
        for month in range(1, 13):
            print(month)

            u_file = f"/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/UAS/uas_{sim.lower()}_{year}{month:02d}_se.nc"
            v_file = f"/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/VAS/vas_{sim.lower()}_{year}{month:02d}_se.nc"
            output_file = f"/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/WIND/wind10_{sim.lower()}_{year}{month:02d}_se.nc"

            try:
                ds_u = xr.open_dataset(u_file)
            except FileNotFoundError:
                print(f"File not found: {u_file}, skipping.")
                continue
            ds_v = xr.open_dataset(v_file)

            wind_magnitude = np.sqrt(ds_u['uas']**2 + ds_v['vas']**2)

            ds_wind = xr.Dataset({'surf_wind': wind_magnitude})

            ds_wind['surf_wind'].attrs['long_name'] = "Near-Surface Wind Magnitude"
            ds_wind['surf_wind'].attrs['units'] = "m/s"
            ds_wind['surf_wind'].attrs['description'] = "Near-Surface Wind Magnitude calculated from uas and vas components"

            for_pole = xr.open_dataset('/home/vdemeyer/projects/rrg-gachon/vdemeyer/UBB/PR/pr_ubb_202001_se.nc')
            ds_wind["rotated_pole"] = for_pole["rotated_pole"]
            attrs_to_copy = [
                "grid_mapping_name",
                "grid_north_pole_latitude",
                "grid_north_pole_longitude",
                "north_pole_grid_longitude"
            ]
            for attr in attrs_to_copy:
                if attr in for_pole.attrs:
                    ds_wind.attrs[attr] = for_pole.attrs[attr]

            ds_wind.to_netcdf(output_file)
            print(f"Saved {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate wind magnitude for a given simulation.")
    parser.add_argument("sim", type=str, help="Simulation for which to calculate wind magnitude")
    args = parser.parse_args()
    main(args.sim)

# run /home/vdemeyer/DATA_COMPUTING/Calculate_Wind_Magnitude.py UBI