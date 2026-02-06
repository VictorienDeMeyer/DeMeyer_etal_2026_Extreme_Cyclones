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
from matplotlib.ticker import AutoMinorLocator

#run /home/vdemeyer/TRACKING/KATJA/POSTPROCESSING/plot_POE_PDF_EETCS_stat.py

simulations = ['ERA5', 'UBB', 'UBD', 'UBE', 'UBF']
quantiles = [0.98, 0.99, 0.995, 0.999]
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

EETC_dict_norm = {}
EETC_dict = {}
sorted_EETC_cum_rank_sim = {}

for quantile in quantiles:
    print(f"Processing quantile: {quantile}")

    for sim in simulations:
        print(f"\nProcessing simulation: {sim}")
        (
            sorted_EETC_cum_rank,
            _,
            _,
            _,
            _,
            _,
            _,
            _,
            _,
            EETC_dict_norm_sim
        ) = calculate_ranking(sim=sim, quantile=quantile, ref=ref, method='product') #LA MÉTHODE N'A PAS D'INCIDENCE POUR LES PLOTS DE PDF !!! la méthode change le ranking des EETCs, pas la distinction EETC vs ETC

        sorted_EETC_cum_rank_sim[sim] = {
            "sorted_EETC_cum_rank": sorted_EETC_cum_rank,
        }
        
        _, EETC_dict_sim = open_files(sim, ref=ref)

        EETC_dict_norm[sim] = EETC_dict_norm_sim
        EETC_dict[sim] = EETC_dict_sim

    plot_params = [
        {
            "var": "cum_precip",
            "label": '$ETC_{PR, cum}$',
            "ax_index": (0, 0)
        },
        {
            "var": "cum_avg_precip",
            "label": '$\overline{{ETC}_{PR}}$',
            "ax_index": (0, 1)
        },
        {
            "var": "SSI",
            "label": '$SSI$',
            "ax_index": (1, 0)
        },
        {
            "var": "cum_avg_wind",
            "label": '$\overline{{ETC}_{WS}}$',
            "ax_index": (1, 1)
        }
    ]

        
###############################################################################################################   


    fig, axes = plt.subplots(2, 2, figsize=(12, 12), constrained_layout=True)

    colors = ['k', 'blue', 'red', 'green', 'purple']

    EETCs = [sorted_EETC_cum_rank_sim[sim]["sorted_EETC_cum_rank"] for sim in simulations]  # Random ranking --> we just need all ETCs, that are not dependent on the ranking method

    for params in plot_params:
        ax = axes[params["ax_index"]]
        
        for isim, sim in enumerate(simulations):
            if norm == True:
                EETCs_var = [EETC_dict_norm[sim][k][params["var"]].sel(quantile=quantile).values for k in EETCs[isim]]
            else:
                EETCs_var = [EETC_dict[sim][k][params["var"]].sel(quantile=quantile).values for k in EETCs[isim]]
        
            kde = gaussian_kde(EETCs_var)
            vals = np.linspace(min(EETCs_var), max(EETCs_var), 1000)
            density = kde(vals)
            density /= density.max()  # Normalize density
            ax.plot(vals, density, color=colors[isim % len(colors)], linestyle='-', label=sim, linewidth=3)
            
        ax.set_xlim(0, None)
        ax.set_ylim(0, 1)
        # ax.set_xscale('log')
        ax.set_xlabel("Metric value", fontsize=15)
        ax.set_ylabel("Normalized Density", fontsize=15)
        ax.set_title(params["label"], fontsize=15)
        ax.legend(fontsize=12, loc='upper right')
        ax.tick_params(axis='both', which='major', labelsize=12, width=2, length=6)
        ax.tick_params(axis='both', which='minor', labelsize=10, width=1.5, length=4)
        ax.xaxis.set_minor_locator(AutoMinorLocator())
        ax.minorticks_on()
        ax.grid(True, which='major', axis='both', linestyle='-', linewidth=0.3, c='black')
        ax.grid(True, which='minor', axis='y', linestyle='--', linewidth=0.2)
        

    fig.suptitle(f"PDF of the strongest ETCs over Québec from 1979 to 2014 or 2023 — ${quantile*100:.1f}^{{th}}$ percentile", fontsize=16)

    plt.savefig(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/PLOT/EETCs_PDF_Quebec_allyears_{quantile*100:.1f}-percentile{ref_str}{norm_str}.png', dpi=70, bbox_inches='tight')
    plt.close(fig)
    
    
###############################################################################################################     


    fig, axes = plt.subplots(2, 2, figsize=(12, 12), constrained_layout=True)

    colors = ['k', 'blue', 'red', 'green', 'purple']

    EETCs = [sorted_EETC_cum_rank_sim[sim]["sorted_EETC_cum_rank"] for sim in simulations]  # Random ranking --> we just need all ETCs, that are not dependent on the ranking method

    for params in plot_params:
        ax = axes[params["ax_index"]]
        
        for isim, sim in enumerate(simulations):
            if norm == True:
                EETCs_var = [EETC_dict_norm[sim][k][params["var"]].sel(quantile=quantile).values for k in EETCs[isim]]
            else:
                EETCs_var = [EETC_dict[sim][k][params["var"]].sel(quantile=quantile).values for k in EETCs[isim]]
            
            # Sort values for probability of exceedance
            sorted_vals = np.sort(EETCs_var)[::-1]  # Sort in descending order
            prob_exceedance = np.arange(1, len(sorted_vals) + 1) / len(sorted_vals)  # Calculate exceedance probability
            
            ax.plot(sorted_vals, np.log10(prob_exceedance*100), color=colors[isim % len(colors)], linestyle='-', label=sim, linewidth=3)
            
        ax.set_xlim(0, None)
        ax.set_ylim(top=2)
        # ax.set_yscale('log')  # Set y-axis to logarithmic scale
        ax.set_xlabel("Metric value", fontsize=15)
        ax.set_ylabel("log(Probability of Exceedance)", fontsize=15)
        ax.set_title(params["label"], fontsize=15)
        ax.legend(fontsize=12, loc='upper right')
        ax.tick_params(axis='both', which='major', labelsize=12, width=2, length=6)
        ax.tick_params(axis='both', which='minor', labelsize=10, width=1.5, length=4)
        ax.xaxis.set_minor_locator(AutoMinorLocator())
        ax.minorticks_on()
        ax.grid(True, which='major', axis='both', linestyle='-', linewidth=0.3, c='black')
        ax.grid(True, which='minor', axis='y', linestyle='--', linewidth=0.2)

    fig.suptitle(f"Probability of Exceedance of the strongest ETCs over Québec from 1979 to 2014 or 2023 — ${quantile*100:.1f}^{{th}}$ percentile", fontsize=16) 
        
    plt.savefig(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/PLOT/EETCs_POE_Quebec_allyears_{quantile*100:.1f}-percentile{ref_str}{norm_str}.png', dpi=70, bbox_inches='tight')
    plt.close(fig)