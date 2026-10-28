import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'POSTPROCESSING'))

from cyclone_phase_space import GridGeometry, cps_parameters, storm_headings, bearing
from classify_cyclone_phase import label_storm, running_mean, interpolate_to_track

"""
Light sanity checks of the cyclone phase space diagnostics on synthetic fields
(a few seconds, can run on a login node):
    python /home/vdemeyer/TRACKING/KATJA/TESTS/test_cyclone_phase.py
"""

LEVELS = [900, 850, 800, 700, 600, 500, 400, 300]
LAT0, LON0 = 30., -60.


def synthetic_field(amplitude, thickness_gradient=0.):
    """
    Gaussian low centered on (LAT0, LON0) on a 0.25 deg grid.

    :param amplitude: dict level -> depth of the low [m].
    :param thickness_gradient: northward decrease of Z600 [m per km], i.e. the
        900-600 hPa thickness is larger to the south.
    """
    lat = np.arange(15., 45.01, 0.25)
    lon = np.arange(-80., -39.99, 0.25)
    lon2d, lat2d = np.meshgrid(lon, lat)
    dist_north = (lat2d - LAT0) * 111.2
    r2 = ((lat2d - LAT0) * 111.2)**2 + ((lon2d - LON0) * 111.2 * np.cos(np.radians(LAT0)))**2
    z = np.stack([5000. - amplitude[p] * np.exp(-r2 / (2 * 400.**2)) for p in LEVELS])
    z[LEVELS.index(600)] -= thickness_gradient * dist_north
    return z.reshape(len(LEVELS), -1), GridGeometry(lat2d, lon2d)


def depth(values):
    return dict(zip(LEVELS, values))


def test_thermal_wind():
    warm = depth([100, 95, 90, 80, 70, 60, 50, 40])     # low weakens with height
    cold = depth([40, 50, 60, 70, 80, 90, 100, 110])    # low deepens with height
    shallow = depth([100, 95, 90, 80, 70, 80, 95, 110])  # warm seclusion: warm below 600 hPa, cold above

    z, geom = synthetic_field(warm)
    B, vtl, vtu, cov = cps_parameters(z, LEVELS, LAT0, LON0, 90., geom)
    assert cov > 0.95, cov
    assert abs(B) < 1., B
    assert vtl > 0 and vtu > 0, (vtl, vtu)

    z, geom = synthetic_field(cold)
    _, vtl, vtu, _ = cps_parameters(z, LEVELS, LAT0, LON0, 90., geom)
    assert vtl < 0 and vtu < 0, (vtl, vtu)

    z, geom = synthetic_field(shallow)
    _, vtl, vtu, _ = cps_parameters(z, LEVELS, LAT0, LON0, 90., geom)
    assert vtl > 0 and vtu < 0, (vtl, vtu)
    print('thermal wind: OK')


def test_thermal_asymmetry():
    sym = depth([50] * len(LEVELS))
    z, geom = synthetic_field(sym, thickness_gradient=0.1)
    # Eastward motion: the warm (thick) side is on the right -> B > 0, about 0.1 * 2 * 4R/(3 pi) = 42 m
    B_east, _, _, _ = cps_parameters(z, LEVELS, LAT0, LON0, 90., geom)
    assert 35. < B_east < 50., B_east
    # Westward motion: warm side on the left -> B < 0
    B_west, _, _, _ = cps_parameters(z, LEVELS, LAT0, LON0, 270., geom)
    assert -50. < B_west < -35., B_west
    # Northward motion: gradient along the motion -> B ~ 0
    B_north, _, _, _ = cps_parameters(z, LEVELS, LAT0, LON0, 0., geom)
    assert abs(B_north) < 2., B_north
    # Undefined heading -> undefined B
    B_nan, _, _, _ = cps_parameters(z, LEVELS, LAT0, LON0, np.nan, geom)
    assert np.isnan(B_nan)
    print(f'thermal asymmetry: OK (B east = {B_east:.1f} m, west = {B_west:.1f} m, north = {B_north:.1f} m)')


def test_coverage():
    z, geom = synthetic_field(depth([50] * len(LEVELS)))
    # Center on the western border of the grid: about half of the disk is missing
    _, _, _, cov = cps_parameters(z, LEVELS, LAT0, -80., 90., geom, min_coverage=0.)
    assert 0.4 < cov < 0.6, cov
    B, vtl, _, _ = cps_parameters(z, LEVELS, LAT0, -81., 90., geom)
    assert np.isnan(B) and np.isnan(vtl)
    print(f'coverage: OK ({cov:.2f} on the border)')


def test_headings():
    dates = pd.date_range('2000-01-01', periods=13, freq='h')
    df = pd.DataFrame({'storm': 1, 'date': dates, 'lat': 40., 'lon': np.linspace(-70., -64., 13)})
    h = storm_headings(df)
    assert np.allclose(h, 90., atol=2.5), h.values
    assert abs(bearing(40., -70., 41., -70.)) < 1e-6
    print('headings: OK')


def run_labels(segments):
    """segments: list of (hours, B, -VTL, -VTU)."""
    B, vtl, vtu = [], [], []
    for hours, b, l, u in segments:
        B += [b] * hours
        vtl += [l] * hours
        vtu += [u] * hours
    t = np.arange(len(B), dtype=float)
    lat = np.full(len(B), 30.)
    return label_storm(np.array(B, float), np.array(vtl, float), np.array(vtu, float), lat, t)


def test_labels():
    labels, tc = run_labels([(72, 30., -40., -60.)])
    assert not tc and set(labels) == {'ETC'}

    # Warm seclusion (symmetric, shallow warm core) stays extratropical
    labels, tc = run_labels([(24, 30., -40., -60.), (48, 3., 20., -30.), (24, 20., -10., -30.)])
    assert not tc and set(labels) == {'ETC'}

    # Short spurious deep warm core is not a tropical phase
    labels, tc = run_labels([(24, 30., -40., -60.), (12, 3., 20., 20.), (24, 30., -40., -60.)])
    assert not tc and set(labels) == {'ETC'}

    # Tropical cyclone -> extratropical transition -> extratropical cyclone
    labels, tc = run_labels([(48, 2., 50., 50.), (24, 20., 20., -10.), (48, 30., -30., -40.)])
    assert tc
    assert list(labels[:48]) == ['TC'] * 48
    assert list(labels[48:72]) == ['TRANSITION'] * 24
    assert list(labels[72:]) == ['ETC'] * 48

    # Cold core first, then asymmetric (other ET pathway)
    labels, tc = run_labels([(48, 2., 50., 50.), (24, 5., -10., -20.), (24, 30., -30., -40.)])
    assert list(labels[48:72]) == ['TRANSITION'] * 24 and list(labels[72:]) == ['ETC'] * 24

    # Tropical cyclone dissipating before ET completion
    labels, tc = run_labels([(48, 2., 50., 50.), (24, 20., 20., -10.)])
    assert list(labels[48:]) == ['TRANSITION'] * 24

    # Tropical transition of an extratropical precursor
    labels, tc = run_labels([(24, 30., -20., -30.), (12, 5., -5., -5.), (48, 2., 50., 50.)])
    assert list(labels[:24]) == ['ETC'] * 24
    assert list(labels[24:36]) == ['TRANSITION'] * 12
    assert list(labels[36:]) == ['TC'] * 48

    # Undefined CPS values do not change the phase
    labels, tc = run_labels([(48, 2., 50., 50.), (12, np.nan, np.nan, np.nan), (24, 30., -30., -40.)])
    assert list(labels[48:60]) == ['TC'] * 12 and list(labels[60:]) == ['ETC'] * 24
    print('labels: OK')


def test_smoothing_interpolation():
    t = np.arange(0., 49., 6.)
    v = np.where(t == 24., 100., 0.)
    s = running_mean(t, v)
    assert np.isclose(s[4], 20.) and np.isclose(s[0], 0.)
    t_track = np.arange(0., 61.)
    out = interpolate_to_track(t, s, t_track)
    assert np.isclose(out[3], 0.5 * (s[0] + s[1]))
    assert np.isfinite(out[60]) and np.isnan(interpolate_to_track(t, s, np.array([61.]))[0])
    print('smoothing and interpolation: OK')


def test_open_zg():
    """CRCM6-like (zg in m, plev in Pa, 2D lat/lon) and ERA5-like (z in m2 s-2, level in hPa) files."""
    import tempfile
    import xarray as xr
    from cyclone_phase_space import open_zg

    levels = [900, 600, 300]
    time = pd.date_range('2000-01-01', periods=4, freq='6h')
    with tempfile.TemporaryDirectory() as tmp:
        crcm = xr.Dataset(
            {'zg': (('time', 'plev', 'rlat', 'rlon'), np.ones((4, 4, 3, 5), 'f4') * 1000.,
                    {'units': 'm'})},
            coords={'time': time + pd.Timedelta('1ns'), 'plev': ('plev', [90000., 70000., 60000., 30000.], {'units': 'Pa'}),
                    'rlat': np.arange(3.), 'rlon': np.arange(5.),
                    'lat': (('rlat', 'rlon'), np.ones((3, 5)) * 40.), 'lon': (('rlat', 'rlon'), np.ones((3, 5)) * -60.)})
        crcm.to_netcdf(f'{tmp}/crcm.nc')
        zg, lat2d, lon2d = open_zg([f'{tmp}/crcm.nc'], levels)
        assert list(zg['plev'].values) == levels and zg.shape == (4, 3, 3, 5) and lat2d.shape == (3, 5)
        assert pd.DatetimeIndex(zg['time'].values).equals(time)

        era5 = xr.Dataset(
            {'z': (('time', 'level', 'latitude', 'longitude'), np.ones((4, 3, 3, 5), 'f4') * 9806.65,
                   {'units': 'm**2 s**-2'})},
            coords={'time': time, 'level': ('level', [300, 600, 900], {'units': 'millibars'}),
                    'latitude': [45., 44.75, 44.5], 'longitude': np.arange(5.) * 0.25 + 280.})
        era5.to_netcdf(f'{tmp}/era5.nc')
        zg, lat2d, lon2d = open_zg([f'{tmp}/era5.nc'], levels)
        assert list(zg['plev'].values) == levels and np.allclose(zg.values, 1000.) and lat2d.shape == (3, 5)
    print('geopotential files: OK')


def test_phase_file_roundtrip():
    """classify -> phase file -> ETC_tools.open_df with the three tc_filter options."""
    import tempfile
    import ETC_tools
    from classify_cyclone_phase import classify

    dates_tc = pd.date_range('1990-09-01', periods=96, freq='h')
    dates_etc = pd.date_range('1990-09-02', periods=48, freq='h')
    track = pd.concat([
        pd.DataFrame({'storm': 1, 'point': np.arange(1, 97), 'i': 1, 'j': 1, 'date': dates_tc,
                      'lat': np.linspace(25., 45., 96), 'lon': -70., 'pressure': 990.}),
        pd.DataFrame({'storm': 2, 'point': np.arange(1, 49), 'i': 1, 'j': 1, 'date': dates_etc,
                      'lat': 50., 'lon': np.linspace(-90., -60., 48), 'pressure': 995.}),
    ], ignore_index=True)
    # 6-hourly CPS: storm 1 tropical for 48 h then extratropical, storm 2 extratropical
    cps = []
    for storm, dates, segments in [(1, dates_tc, [(48, 2., 50., 50.), (48, 30., -30., -40.)]),
                                   (2, dates_etc, [(48, 30., -30., -40.)])]:
        values = np.concatenate([np.tile([b, l, u], (h, 1)) for h, b, l, u in segments])
        sel = dates.hour % 6 == 0
        cps.append(pd.DataFrame({'storm': storm, 'date': dates[sel], 'B': values[sel, 0],
                                 'minus_VTL': values[sel, 1], 'minus_VTU': values[sel, 2]}))
    labelled = classify(track, pd.concat(cps, ignore_index=True))

    old_prefix = ETC_tools._FILE_PREFIX
    with tempfile.TemporaryDirectory() as tmp:
        try:
            ETC_tools._FILE_PREFIX = f'{tmp}/'
            os.makedirs(f'{tmp}/UBD/STORM_RELATED/TRACK')
            track.to_csv(ETC_tools.track_file('UBD'), sep=' ', index=False)
            labelled.to_csv(ETC_tools.phase_file('UBD'), sep=' ', index=False, float_format='%.4f',
                            date_format='%Y-%m-%d %H:%M:%S')
            all_points = ETC_tools.open_df('UBD', period_filtering=False)
            phase = ETC_tools.open_df('UBD', period_filtering=False, tc_filter='phase')
            storm = ETC_tools.open_df('UBD', period_filtering=False, tc_filter='storm')
            flagged = ETC_tools.open_df('UBD', period_filtering=False, tc_filter='phase', keep_non_etc=True)
        finally:
            ETC_tools._FILE_PREFIX = old_prefix

    assert len(all_points) == 144 and len(flagged) == 144
    assert set(storm['storm']) == {2} and len(storm) == 48
    s1 = phase[phase['storm'] == 1]
    assert 0 < len(s1) < 96 and s1['date'].min() > dates_tc[47]
    assert len(phase[phase['storm'] == 2]) == 48
    assert flagged['is_etc'].sum() == len(phase) and phase['date'].dtype.kind == 'M'
    print(f'phase file round trip: OK (storm 1: {96 - len(s1)} non-ETC hours removed)')


def test_ibtracs_matching():
    from validate_phase_ibtracs import match_points
    dates = pd.date_range('2000-08-01', periods=6, freq='6h')
    track = pd.DataFrame({'storm': [7] * 6 + [8] * 6, 'date': list(dates) * 2,
                          'lat': [30.] * 6 + [50.] * 6, 'lon': [-70.] * 6 + [-40.] * 6,
                          'phase': ['TC'] * 6 + ['ETC'] * 6, 'tc_storm': [True] * 6 + [False] * 6})
    ib = pd.DataFrame({'SID': 'A', 'NAME': 'TEST', 'date': dates, 'NATURE': 'TS',
                       'LAT': 31., 'LON': -70.5})
    m = match_points(track, ib)
    assert set(m['storm']) == {7} and len(m) == 6
    print('IBTrACS matching: OK')


if __name__ == '__main__':
    test_thermal_wind()
    test_thermal_asymmetry()
    test_coverage()
    test_headings()
    test_labels()
    test_smoothing_interpolation()
    test_open_zg()
    test_phase_file_roundtrip()
    test_ibtracs_matching()
    print('\nAll tests passed')
