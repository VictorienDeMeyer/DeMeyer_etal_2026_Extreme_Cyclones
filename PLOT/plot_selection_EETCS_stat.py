import pandas as pd
from glob import glob
from braceexpand import braceexpand
import numpy as np
import matplotlib.pyplot as plt
import pickle
import xarray as xr
from scipy.stats import gaussian_kde
from matplotlib.ticker import ScalarFormatter
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..', 'POSTPROCESSING')))

#run /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/plot_selection_EETCS_stat.py

simulations = ['ERA5', 'UBB', 'UBD', 'UBE', 'UBF']
quantiles = [0.98, 0.99, 0.995, 0.999]
method = 'borda' #'borda' #the method will just change the selection of the strongest EETCs, not the distribution of EETCs. It has little effect on the selection.
ref = True #False #the ref parameter is useful to compare simulations with each other. If it is false, it might be better so set norm to True to compare simulations with a normalization.
norm = False #True #the norm parameter will normalize the metric values between 0 and 1. It is useful to compare simulations that do not share the same ref (each their own percentile)

if ref == True:
    ref_str = '_ref_ERA5'
else:
    ref_str = ''
    
if norm == True:
    norm_str = '_norm'
else:
    norm_str = ''

for sim in simulations:
    print(f"\nProcessing simulation: {sim}")

    if sim == 'UBB' or sim == 'ERA5':
        endyear = 2023
    else:
        endyear = 2014

    df,_ = open_files(sim)

    for quantile in quantiles:
        print(f"Processing quantile: {quantile}")

        (
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
        ) = calculate_ranking(sim=sim, quantile=quantile, ref=ref, method=method)

        for storm in EETC_dict:
            if EETC_dict[storm]['cum_precip'].sel(quantile=quantile).values or EETC_dict[storm]['cum_avg_precip'].sel(quantile=quantile).values or EETC_dict[storm]['cum_wind'].sel(quantile=quantile).values or EETC_dict[storm]['cum_avg_wind'].sel(quantile=quantile).values or EETC_dict[storm]['SSI'].sel(quantile=quantile).values != 0:
                storm_group = df.groupby('storm').get_group(storm)
                min_pressure_row = storm_group.loc[storm_group['pressure'].idxmin()]
                EETC_dict[storm]['min_pressure_date'] = min_pressure_row['date']
        
        plot_params = [
            {
                "var_precip": "cum_precip",
                "var_wind": "cum_wind",
                "rank_var": sorted_EETC_cum_rank,
                "ylabel": '$ETC_{PR, cum}$',
                "xlabel": '$ETC_{WS, cum}$',
                "colors": combined_scores,
                "ax_index": (0, 0)
            },
            {
                "var_precip": "cum_avg_precip",
                "var_wind": "cum_avg_wind",
                "rank_var": sorted_EETC_cum_avg_rank,
                "ylabel": '$\overline{{ETC}_{PR}}$',
                "xlabel": '$\overline{{ETC}_{WS}}$',
                "colors": combined_avg_scores,
                "ax_index": (0, 1)
            },
            {
                "var_precip": "cum_precip",
                "var_wind": "SSI",
                "rank_var": sorted_EETC_cum_SSI_rank,
                "ylabel": '$ETC_{PR, cum}$',
                "xlabel": '$SSI$',
                "colors": combined_SSI_scores,
                "ax_index": (1, 0)
            },
            {
                "var_precip": "cum_avg_precip",
                "var_wind": "SSI",
                "rank_var": sorted_EETC_cum_avg_SSI_rank,
                "ylabel": '$\overline{{ETC}_{PR}}$',
                "xlabel": '$SSI$',
                "colors": combined_SSI_avg_scores,
                "ax_index": (1, 1)
            }
        ]
        
        
####################################################################################################################################


        fig, axes = plt.subplots(2, 2, figsize=(16, 16), constrained_layout=True)

        for params in plot_params:

            if norm == True:
                x = [EETC_dict_norm[k][params["var_wind"]].sel(quantile=quantile).values for k in params["rank_var"]]
                y = [EETC_dict_norm[k][params["var_precip"]].sel(quantile=quantile).values for k in params["rank_var"]]
                colors = []
                for k in params["rank_var"]:
                    month = EETC_dict_norm[k]['min_pressure_date'].month
                    for season, months in seasons.items():
                        if month in months:
                            colors.append(season_color[season])
                            break
            else:
                x = [EETC_dict[k][params["var_wind"]].sel(quantile=quantile).values for k in params["rank_var"]]
                y = [EETC_dict[k][params["var_precip"]].sel(quantile=quantile).values for k in params["rank_var"]]
                colors = []
                for k in params["rank_var"]:
                    month = EETC_dict[k]['min_pressure_date'].month
                    for season, months in seasons.items():
                        if month in months:
                            colors.append(season_color[season])
                            break
                
            ax = axes[params["ax_index"]]
            if method == 'product':
                vmax = 0.10
                # vmax = max(combined_scores[sorted_EETC_cum_rank[0]], combined_avg_scores[sorted_EETC_cum_avg_rank[0]],
                # combined_SSI_scores[sorted_EETC_cum_SSI_rank[0]], combined_SSI_avg_scores[sorted_EETC_cum_avg_SSI_rank[0]])
                cmap = 'jet'
            else:
                vmax = 400
                cmap = 'jet_r'

            sc = ax.scatter(x, y, c=colors, s=20, alpha=0.5, cmap=cmap, vmin=0, vmax=vmax)

            for i in range(6):
                ax.scatter(x[i], y[i], c=colors[i], s=50, cmap=cmap, vmin=sc.norm.vmin, vmax=sc.norm.vmax)
                if norm == True:
                    ax.annotate(f"{EETC_dict_norm[params['rank_var'][i]]['min_pressure_date'].month}-{EETC_dict_norm[params['rank_var'][i]]['min_pressure_date'].year}", (x[i], y[i]), fontsize=10)
                else:
                    ax.annotate(f"{EETC_dict[params['rank_var'][i]]['min_pressure_date'].month}-{EETC_dict[params['rank_var'][i]]['min_pressure_date'].year}", (x[i], y[i]), fontsize=10)
            
            if norm == False:
                ax_twinx = ax.twinx()
                kde_x = gaussian_kde(x)
                x_vals = np.linspace(min(x), max(x), 1000)
                density_x = kde_x(x_vals)
                density_x /= density_x.max()  # Normalisation de la densité
                ax_twinx.fill_between(x_vals, density_x, color='blue', alpha=0.2)
                ax_twinx.set_ylim(0, 1)
                ax_twinx.tick_params(axis='y', which='major', labelsize=12, width=2, length=6)
                ax_twinx.tick_params(axis='y', which='minor', labelsize=10, width=1.5, length=4)
                ax_twinx.set_ylabel('PDF', fontsize=15)

                ax_twiny = ax.twiny()
                kde_y = gaussian_kde(y)
                y_vals = np.linspace(min(y), max(y), 1000)
                density_y = kde_y(y_vals)
                density_y /= density_y.max()
                ax_twiny.fill_betweenx(y_vals, density_y, color='red', alpha=0.2)
                ax_twiny.set_xlim(0, 1)
                ax_twiny.tick_params(axis='x', which='major', labelsize=12, width=2, length=6)
                ax_twiny.tick_params(axis='x', which='minor', labelsize=10, width=1.5, length=4)
                ax_twiny.set_xlabel('PDF', fontsize=15)
                
            else:
                kde_x = gaussian_kde(x)
                x_vals = np.linspace(min(x), max(x), 1000)
                density_x = kde_x(x_vals)
                density_x /= density_x.max()
                ax.fill_between(x_vals, density_x, color='blue', alpha=0.2)

                kde_y = gaussian_kde(y)
                y_vals = np.linspace(min(y), max(y), 1000)
                density_y = kde_y(y_vals)
                density_y /= density_y.max()
                ax.fill_betweenx(y_vals, density_y, color='red', alpha=0.2)

            ax.set_xlim(left=0)
            ax.set_ylim(bottom=0)
            ax.set_xlabel(params["xlabel"], fontsize=15)
            ax.set_ylabel(params["ylabel"], fontsize=15)

            ax.tick_params(axis='both', which='major', labelsize=12, width=2, length=6)
            ax.tick_params(axis='both', which='minor', labelsize=10, width=1.5, length=4)

        cbar = fig.colorbar(sc, ax=axes, orientation='vertical', shrink=0.8, pad=0.02, aspect=40, extend='max')
        if method == 'borda':
            cbar.ax.invert_yaxis()
            cbar.set_label('Ranking with borda method', fontsize=12)
        else:
            cbar.set_label('Product of both metrics normalized', fontsize=12)

        fig.suptitle(f"{sim} strongest ETCs over Québec from 1979 to {endyear} - ${quantile*100:.1f}^{{th}}$ percentile", fontsize=16)

        plt.savefig(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/PLOT/{sim}_EETCs_2D_PDF_Quebec_1979-{endyear}_{quantile*100:.1f}-percentile_{method}{ref_str}{norm_str}.png', dpi=70, bbox_inches='tight')
        plt.close(fig)
        
        
####################################################################################################################################


        fig, axes = plt.subplots(2, 2, figsize=(16, 16), constrained_layout=True)

        for params in plot_params:

            if norm == True:
                x = [EETC_dict_norm[k][params["var_wind"]].sel(quantile=quantile).values for k in params["rank_var"]]
                y = [EETC_dict_norm[k][params["var_precip"]].sel(quantile=quantile).values for k in params["rank_var"]]
                colors = []
                for k in params["rank_var"]:
                    month = EETC_dict_norm[k]['min_pressure_date'].month
                    for season, months in seasons.items():
                        if month in months:
                            colors.append(season_color[season])
                            break
            else:
                x = [EETC_dict[k][params["var_wind"]].sel(quantile=quantile).values for k in params["rank_var"]]
                y = [EETC_dict[k][params["var_precip"]].sel(quantile=quantile).values for k in params["rank_var"]]
                colors = []
                for k in params["rank_var"]:
                    month = EETC_dict[k]['min_pressure_date'].month
                    for season, months in seasons.items():
                        if month in months:
                            colors.append(season_color[season])
                            break
                
            ax = axes[params["ax_index"]]
            vmax = 0.10

            sc = ax.scatter(x, y, c=colors, s=20, alpha=0.5, cmap='jet', vmin=0, vmax=vmax)

            for i in range(6):
                ax.scatter(x[i], y[i], c=colors[i], s=50, cmap='jet', vmin=sc.norm.vmin, vmax=sc.norm.vmax)
                if norm == True:
                    ax.annotate(f"{EETC_dict_norm[params['rank_var'][i]]['min_pressure_date'].month}-{EETC_dict_norm[params['rank_var'][i]]['min_pressure_date'].year}", (x[i], y[i]), fontsize=10)
                else:
                    ax.annotate(f"{EETC_dict[params['rank_var'][i]]['min_pressure_date'].month}-{EETC_dict[params['rank_var'][i]]['min_pressure_date'].year}", (x[i], y[i]), fontsize=10)

            kde = gaussian_kde([x, y])
            x_grid, y_grid = np.mgrid[min(x):max(x):100j, min(y):max(y):100j]
            grid_positions = np.vstack([x_grid.ravel(), y_grid.ravel()])
            density = kde(grid_positions).reshape(x_grid.shape)
            density /= density.max()
            kde_2D = ax.contour(x_grid, y_grid, density, levels=100, cmap='gist_ncar', alpha=0.5)

            if norm == True:
                ax.set_xlim(0, 1.05)
                ax.set_ylim(0, 1.05)
            else:   
                ax.set_xlim(left=0)
                ax.set_ylim(bottom=0)
            ax.set_xlabel(params["xlabel"], fontsize=15)
            ax.set_ylabel(params["ylabel"], fontsize=15)

            ax.tick_params(axis='both', which='major', labelsize=12, width=2, length=6)
            ax.tick_params(axis='both', which='minor', labelsize=10, width=1.5, length=4)

        norma = plt.Normalize(vmin=0, vmax=1)
        sm = plt.cm.ScalarMappable(cmap='gist_ncar', norm=norma)
        sm.set_array([])
        cbar_kde_2D = fig.colorbar(sm, ax=axes, orientation='vertical', shrink=0.8, pad=0.02, aspect=40)
        cbar_kde_2D.set_label('Normalized Density', fontsize=12)
        cbar_kde_2D.set_ticks([0, 0.25, 0.5, 0.75, 1])
        cbar_kde_2D.set_ticklabels(['0', '0.25', '0.5', '0.75', '1'])

        cbar = fig.colorbar(sc, ax=axes, orientation='vertical', shrink=0.8, pad=0.02, aspect=40, extend='max')
        if method=='borda':
            cbar.set_label('Ranking with borda method', fontsize=12)
            cbar.ax.invert_yaxis()
        else:
            cbar.set_label('Product of both metrics normalized', fontsize=12)

        fig.suptitle(f"{sim} strongest ETCs over Québec from 1979 to {endyear} - ${quantile*100:.1f}^{{th}}$ percentile", fontsize=16)
        
        plt.savefig(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/PLOT/{sim}_EETCs_3D_PDF_Quebec_1979-{endyear}_{quantile*100:.1f}-percentile_{method}{ref_str}{norm_str}.png', dpi=70, bbox_inches='tight')
        plt.close(fig)
        
        
####################################################################################################################################


        fig, axes = plt.subplots(2, 2, figsize=(16, 16), constrained_layout=True)

        seasons = {'DJF': [12, 1, 2], 'MAM': [3, 4, 5], 'JJA': [6, 7, 8], 'SON': [9, 10, 11]}
        season_color = {'DJF': '#7eb7de', 'MAM': '#2ca02c', 'JJA': '#ff7f0e', 'SON': '#d62728'}

        for params in plot_params:      

            if norm == True:
                x = [EETC_dict_norm[k][params["var_wind"]].sel(quantile=quantile).values for k in params["rank_var"]]
                y = [EETC_dict_norm[k][params["var_precip"]].sel(quantile=quantile).values for k in params["rank_var"]]
                colors = []
                for k in params["rank_var"]:
                    month = EETC_dict_norm[k]['min_pressure_date'].month
                    for season, months in seasons.items():
                        if month in months:
                            colors.append(season_color[season])
                            break
            else:
                x = [EETC_dict[k][params["var_wind"]].sel(quantile=quantile).values for k in params["rank_var"]]
                y = [EETC_dict[k][params["var_precip"]].sel(quantile=quantile).values for k in params["rank_var"]]
                colors = []
                for k in params["rank_var"]:
                    month = EETC_dict[k]['min_pressure_date'].month
                    for season, months in seasons.items():
                        if month in months:
                            colors.append(season_color[season])
                            break

            ax = axes[params["ax_index"]]

            sc = ax.scatter(x, y, c=colors, s=60)

            for i in range(6):
                ax.scatter(x[i], y[i], c=colors[i], s=100)
                if norm == True:
                    ax.annotate(f"{EETC_dict_norm[params['rank_var'][i]]['min_pressure_date'].month}-{EETC_dict_norm[params['rank_var'][i]]['min_pressure_date'].year}", (x[i], y[i]), fontsize=10)
                else:
                    ax.annotate(f"{EETC_dict[params['rank_var'][i]]['min_pressure_date'].month}-{EETC_dict[params['rank_var'][i]]['min_pressure_date'].year}", (x[i], y[i]), fontsize=10)
                    
            handles = [plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markersize=10, label=season) 
                       for season, color in season_color.items()]
            ax.legend(handles=handles, title="Seasons", fontsize=10, title_fontsize=12, loc='upper right')

            ax.set_xlim(left=0)
            ax.set_ylim(bottom=0)
            ax.set_xlabel(params["xlabel"], fontsize=15)
            ax.set_ylabel(params["ylabel"], fontsize=15)

            ax.tick_params(axis='both', which='major', labelsize=12, width=2, length=6)
            ax.tick_params(axis='both', which='minor', labelsize=10, width=1.5, length=4)

        fig.suptitle(f"{sim} strongest ETCs over Québec from 1979 to {endyear} - ${quantile*100:.1f}^{{th}}$ percentile", fontsize=16)
        plt.savefig(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/PLOT/{sim}_EETCs_seasons_Quebec_1979-{endyear}_{quantile*100:.1f}-percentile_{method}{ref_str}{norm_str}.png', dpi=70, bbox_inches='tight')
        plt.close(fig)