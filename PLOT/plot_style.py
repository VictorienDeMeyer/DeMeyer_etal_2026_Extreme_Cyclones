import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.ticker import FuncFormatter
from scipy.ndimage import gaussian_filter
import cartopy
import cartopy.crs as ccrs

"""
Map style of the paper figures, copied without change from the helper functions of
PLOT/plot_map_ETCs_diff_w_ERA5.ipynb so that scripts can reuse them:
    import plot_style as S
    fig, axes, crs = S._setup_plot_axes(positions, figsize)
    S._draw_map_features(ax)
    sc, levels = S._plot_data_on_ax(ax, data, crs, 'contourf', 'Spectral_r', vmin, vmax, step, 'max')
    S._add_cbar(fig, sc, cbar_ax, label, 'contourf', levels)

Author: Dr Victorien De Meyer
Year: 2026
"""

def clean_float(x, pos):
    """Formateur pour retirer les notations scientifiques pour les petits nombres."""
    if abs(x) < 1e-8: # seuil de tolérance (adjustable)
        x = 0
    return '%g' % x

def get_colormap(colormap_name, style=None, rework=True):
    """
    Récupère une colormap, avec une modification spéciale pour 'Spectral_r'.
    (Fonction inchangée)
    """
    # Si l'entrée est déjà une colormap (comme cmocean.cm.curl)
    if hasattr(colormap_name, '__call__'):
        return colormap_name

    # Cas spécial pour 'Spectral_r' avec style différent de 'pcolormesh'
    if colormap_name == 'Spectral_r' and style != 'pcolormesh' and rework == True:
        spectral = plt.colormaps['Spectral_r']
        colors = spectral(np.linspace(0, 1, 256))
        colors[128:145] = colors[128:145] * 0.95  # Reduce brightness at the center
        return mcolors.LinearSegmentedColormap.from_list('ModifiedSpectral', colors)

    # Sinon, essaie de la récupérer parmi les colormaps enregistrées (matplotlib ou ajoutées comme cmocean)
    try:
        return plt.get_cmap(colormap_name)
    except ValueError:
        raise ValueError(f"Colormap '{colormap_name}' not found.")

# --- Fonctions refactorées ---

def _setup_plot_axes(positions, figsize, plotcrs=ccrs.LambertConformal(central_latitude=45, central_longitude=-95)):
    """Initialise la figure et les axes Cartopy."""
    if positions is None:
        # Cas classique avec subplots
        fig, axes = plt.subplots(
            subplot_kw={'projection': plotcrs},
            figsize=figsize
        )
        axes = np.atleast_1d(axes).flatten()
    
    else:
        # Cas positions custom
        fig = plt.figure(figsize=figsize)
        axes = [fig.add_axes(pos, projection=plotcrs) for pos in positions]
    crs = ccrs.PlateCarree()
    return fig, axes, crs

def _draw_map_features(ax):
    """Ajoute les entités géographiques (frontières, lacs, grille) à un axe."""
    ax.set_extent([-128, -56, 81, 12], crs=ccrs.PlateCarree())
    
    borders = cartopy.feature.NaturalEarthFeature(category='cultural', name='admin_0_boundary_lines_land', scale='50m', facecolor='none')
    states_provinces = cartopy.feature.NaturalEarthFeature(category='cultural', name='admin_1_states_provinces', scale='50m', facecolor='none')
    lakes_color = cartopy.feature.NaturalEarthFeature(category='physical', name='lakes', scale='50m', facecolor='#7FB4D8', edgecolor='black')
    lakes_edge = cartopy.feature.NaturalEarthFeature(category='physical', name='lakes', scale='50m', facecolor='none', edgecolor='black')
    img = plt.imread('/home/vdemeyer/TOOLS/NE1_50M_SR_W.tif')
    
    ax.imshow(img, origin='upper', extent=(-180, 180, -90, 90), transform=ccrs.PlateCarree())
    ax.add_feature(borders, linewidth=0.5, edgecolor='black', zorder=2)
    ax.add_feature(states_provinces, edgecolor='black', linewidth=0.3)
    ax.add_feature(lakes_color, zorder=1, linewidth=0.3)
    ax.add_feature(lakes_edge, zorder=2, linewidth=0.3)
    ax.coastlines(resolution='10m', linewidth=0.4, color='black')
    ax.gridlines(linewidth=0.5, linestyle='--', color='k', alpha=0.25, xlocs=range(-180,180,10), ylocs=range(-90,90,10))

def _calculate_contourf_levels(vmin, vmax, step, ting):
    """Calcule les niveaux pour contourf, en gérant le cas de symétrie et 'ting'."""
    if step is None:
        raise ValueError("Step cannot be None for contourf style.")
        
    if vmin < 0:
        absmax = max(abs(vmin), abs(vmax))
        # Arrondir absmax au multiple supérieur de step
        nice_max = np.ceil(absmax / step) * step
        vmin = -nice_max
        vmax = +nice_max
        
    if ting:
        # Les niveaux 0.5, 2, 5 sont inclus avant l'échelle régulière
        levels = [0.5, 2, 5] + list(np.arange(10, vmax + step, step))
    else:
        levels = np.arange(vmin, vmax + step, step)
    
    return vmin, vmax, levels

def _plot_data_on_ax(ax, data_xr, crs, style, colormap, vmin, vmax, step, extend_opt, ting=False, 
                     cont=None, sigma=None, contour_levels=None, fmt=None):
    """Effectue le plot (pcolormesh ou contourf) et ajoute les contours."""
    var_lon = 'longitude'
    var_lat = 'latitude'
    
    cmap = get_colormap(colormap, style, rework=(colormap=='Spectral_r' and style != 'pcolormesh')) 
    
    sc = None
    levels = None
    
    if style == 'pcolormesh':
        sc = ax.pcolormesh(
            data_xr[var_lon], data_xr[var_lat], data_xr,
            transform=crs, cmap=cmap, vmin=vmin, vmax=vmax, shading='auto'
        )
    else: # contourf
        vmin, vmax, levels = _calculate_contourf_levels(vmin, vmax, step, ting)
        
        sc = ax.contourf(
            data_xr[var_lon], data_xr[var_lat], data_xr,
            transform=crs, levels=levels + 1e-9, cmap=cmap, vmin=vmin, vmax=vmax, extend=extend_opt
        )
            
    if cont is not None:
        if sigma is not None:
            data_filled = np.nan_to_num(cont.values, nan=0.0)
            smoothed_array = gaussian_filter(data_filled, sigma=sigma, mode='nearest')
            to_plot = np.where(np.isnan(cont.values), np.nan, smoothed_array)
        else:
            to_plot = cont
            
        # to_plot = gaussian_filter(cont, sigma=sigma) if sigma is not None else cont
        
        contours = ax.contour(
            data_xr[var_lon],
            data_xr[var_lat],
            to_plot,
            levels=contour_levels,
            colors='k',
            linewidths=1.6,
            alpha=1.,
            transform=crs,
        )
        ax.clabel(contours, inline=True, fontsize=10, fmt=fmt, inline_spacing=3)
        
    return sc, levels

def _add_cbar(fig, sc, cbar_ax, label, style, levels=None, cb_int=False, extend_opt='both', tick_size=22):
    """Ajoute une barre de couleur standard ou pour contourf avec formatage optionnel."""
    if sc is None:
        return
        
    if style == 'pcolormesh':
        cbar = fig.colorbar(sc, cax=cbar_ax, orientation="horizontal", pad=0.02, extend=extend_opt)
    else:
        cbar = fig.colorbar(sc, cax=cbar_ax, orientation="horizontal", pad=0.02)
        if cb_int and levels is not None:
            int_levels = [l if l == 0.5 else int(l) for l in levels]
            cbar.set_ticklabels(int_levels)
        elif levels is not None:
            cbar.ax.xaxis.set_major_formatter(FuncFormatter(clean_float))
            
    cbar.set_label(label, fontsize=tick_size)
    cbar.ax.tick_params(labelsize=tick_size)
    return cbar
        
