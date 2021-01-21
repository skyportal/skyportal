import itertools

import numpy as np
import pandas as pd

from bokeh.core.properties import List, String
from bokeh.layouts import row, column
from bokeh.models import CustomJS, HoverTool, Range1d, Slider, Button, LinearAxis
from bokeh.models.widgets import CheckboxGroup, TextInput, Panel, Tabs, Div
from bokeh.plotting import figure, ColumnDataSource

import bokeh.embed as bokeh_embed


from astropy.time import Time

from matplotlib import cm
from matplotlib.colors import rgb2hex

import os
from baselayer.app.env import load_env
from skyportal.models import (
    DBSession,
    Obj,
    Photometry,
    Group,
    Instrument,
    Telescope,
    PHOT_ZP,
    Spectrum,
    GroupSpectrum,
)

import sncosmo

_, cfg = load_env()
# The minimum signal-to-noise ratio to consider a photometry point as a detection
PHOT_DETECTION_THRESHOLD = cfg["misc.photometry_detection_threshold_nsigma"]

SPEC_LINES = {
    'H': ([3970, 4102, 4341, 4861, 6563], '#ff0000'),
    'He': ([3886, 4472, 5876, 6678, 7065], '#002157'),
    'He II': ([3203, 4686], '#003b99'),
    'C I': ([8335, 9093, 9406, 9658, 10693, 11330, 11754, 14543], '#8a2be2'),
    'C II': ([3919, 4267, 6580, 7234, 9234], '#570199'),
    'C III': ([4650, 5696], '#a30198'),
    'C IV': ([5801], '#ff0073'),
    'N II': ([5754, 6548, 6583], '#01fee1'),
    'N III': ([4100, 4640], '#01fe95'),
    'O': ([7772, 7774, 7775, 8447, 9266], '#007236'),
    'O II': ([3727], '#00a64d'),
    'O III': ([4959, 5007], '#00bf59'),
    'Na': ([5890, 5896, 8183, 8195], '#aba000'),
    'Mg': ([2780, 2852, 3829, 3832, 3838, 4571, 5167, 5173, 5184], '#8c6239'),
    'Mg II': ([2791, 2796, 2803, 4481], '#bf874e'),
    'Si I': ([10585, 10827, 12032, 15888], '#6495ed'),
    'Si II': ([3856, 5041, 5056, 5670, 6347, 6371], '#5674b9'),
    'S I': ([9223, 10457, 13809, 18940, 22694], '#ffe4b5'),
    'S II': ([5433, 5454, 5606, 5640, 5647, 6715], '#a38409'),
    'Ca I': ([19453, 19753], '#009000'),
    'Ca II': ([3934, 3969, 7292, 7324, 8498, 8542, 8662], '#005050'),
    'Mn I': ([12900, 13310, 13630, 13859, 15184, 15263], '#009090'),
    'Fe I': ([11973], '#cd5c5c'),
    'Fe II': ([5018, 5169], '#f26c4f'),
    'Fe III': ([4397, 4421, 4432, 5129, 5158], '#f9917b'),
    'Co II': (
        [15759, 16064, 16361, 17239, 17462, 17772, 21347, 22205, 22497, 23613, 24596],
        '#ffe4e1',
    ),
}
# TODO add groups
# Galaxy lines
#
# 'H': '4341, 4861, 6563;
# 'N II': '6548, 6583;
# 'O I': '6300;'
# 'O II': '3727;
# 'O III': '4959, 5007;
# 'Mg II': '2798;
# 'S II': '6717, 6731'
# 'H': '3970, 4102, 4341, 4861, 6563'
# 'Na': '5890, 5896, 8183, 8195'
# 'He': '3886, 4472, 5876, 6678, 7065'
# 'Mg': '2780, 2852, 3829, 3832, 3838, 4571, 5167, 5173, 5184'
# 'He II': '3203, 4686'
# 'Mg II': '2791, 2796, 2803, 4481'
# 'O': '7772, 7774, 7775, 8447, 9266'
# 'Si II': '3856, 5041, 5056, 5670 6347, 6371'
# 'O II': '3727'
# 'Ca II': '3934, 3969, 7292, 7324, 8498, 8542, 8662'
# 'O III': '4959, 5007'
# 'Fe II': '5018, 5169'
# 'S II': '5433, 5454, 5606, 5640, 5647, 6715'
# 'Fe III': '4397, 4421, 4432, 5129, 5158'
#
# Other
#
# 'Tel: 6867-6884, 7594-7621'
# 'Tel': '#b7b7b7',
# 'H: 4341, 4861, 6563;
# 'N II': 6548, 6583;
# 'O I': 6300;
# 'O II': 3727;
# 'O III': 4959, 5007;
# 'Mg II': 2798;
# 'S II': 6717, 6731'


class CheckboxWithLegendGroup(CheckboxGroup):
    colors = List(String, help="List of legend colors")

    __implementation__ = ""


tooltip_format = [
    ('mjd', '@mjd{0.000000}'),
    ('flux', '@flux'),
    ('filter', '@filter'),
    ('fluxerr', '@fluxerr'),
    ('mag', '@mag'),
    ('magerr', '@magerr'),
    ('lim_mag', '@lim_mag'),
    ('instrument', '@instrument'),
    ('stacked', '@stacked'),
]
cmap_opt = cm.get_cmap('nipy_spectral')
cmap_uv = cm.get_cmap('cool')
cmap_ir = cm.get_cmap('autumn')


def get_color(bandpass_name):
    if bandpass_name.startswith('ztf'):
        return {'ztfg': 'green', 'ztfi': 'orange', 'ztfr': 'red'}[bandpass_name]
    else:
        bandpass = sncosmo.get_bandpass(bandpass_name)
        wave = bandpass.wave_eff

        if 0 < wave < 3000:
            cmap = cmap_uv
            cmap_limits = (0, 3000)
        elif 3000 <= wave <= 10000:
            cmap = cmap_opt
            cmap_limits = (3000, 10000)
        elif 10000 < wave < 1e5:
            wave = np.log10(wave)
            cmap = cmap_ir
            cmap_limits = (4, 5)
        else:
            raise ValueError('wavelength out of range for color maps')

        rgb = cmap((cmap_limits[1] - wave) / (cmap_limits[1] - cmap_limits[0]))[:3]
        bandcolor = rgb2hex(rgb)

        return bandcolor


def photometry_plot(obj_id, user, width=600, height=300):
    """Create scatter plot of photometry for object.
    Parameters
    ----------
    obj_id : str
        ID of Obj to be plotted.
    Returns
    -------
    (str, str)
        Returns (docs_json, render_items) json for the desired plot.
    """

    data = pd.read_sql(
        DBSession()
        .query(
            Photometry,
            Telescope.nickname.label("telescope"),
            Instrument.name.label("instrument"),
        )
        .join(Instrument, Instrument.id == Photometry.instrument_id)
        .join(Telescope, Telescope.id == Instrument.telescope_id)
        .filter(Photometry.obj_id == obj_id)
        .filter(
            Photometry.groups.any(Group.id.in_([g.id for g in user.accessible_groups]))
        )
        .statement,
        DBSession().bind,
    )

    if data.empty:
        return None, None, None

    data['color'] = [get_color(f) for f in data['filter']]

    labels = []
    for i, datarow in data.iterrows():
        label = f'{datarow["instrument"]}/{datarow["filter"]}'
        if datarow['origin'] is not None:
            label += f'/{datarow["origin"]}'
        labels.append(label)

    data['label'] = labels
    data['zp'] = PHOT_ZP
    data['magsys'] = 'ab'
    data['alpha'] = 1.0
    data['lim_mag'] = (
        -2.5 * np.log10(data['fluxerr'] * PHOT_DETECTION_THRESHOLD) + data['zp']
    )

    # Passing a dictionary to a bokeh datasource causes the frontend to die,
    # deleting the dictionary column fixes that
    del data['original_user_data']

    # keep track of things that are only upper limits
    data['hasflux'] = ~data['flux'].isna()

    # calculate the magnitudes - a photometry point is considered "significant"
    # or "detected" (and thus can be represented by a magnitude) if its snr
    # is above PHOT_DETECTION_THRESHOLD
    obsind = data['hasflux'] & (
        data['flux'].fillna(0.0) / data['fluxerr'] >= PHOT_DETECTION_THRESHOLD
    )
    data.loc[~obsind, 'mag'] = None
    data.loc[obsind, 'mag'] = -2.5 * np.log10(data[obsind]['flux']) + PHOT_ZP

    # calculate the magnitude errors using standard error propagation formulae
    # https://en.wikipedia.org/wiki/Propagation_of_uncertainty#Example_formulae
    data.loc[~obsind, 'magerr'] = None
    coeff = 2.5 / np.log(10)
    magerrs = np.abs(coeff * data[obsind]['fluxerr'] / data[obsind]['flux'])
    data.loc[obsind, 'magerr'] = magerrs
    data['obs'] = obsind
    data['stacked'] = False

    split = data.groupby('label', sort=False)

    finite = np.isfinite(data['flux'])
    fdata = data[finite]
    lower = np.min(fdata['flux']) * 0.95
    upper = np.max(fdata['flux']) * 1.05

    plot = figure(
        aspect_ratio=1.7,
        sizing_mode='scale_both',
        active_drag='box_zoom',
        tools='box_zoom,wheel_zoom,pan,reset,save',
        y_range=(lower, upper),
    )
    imhover = HoverTool(tooltips=tooltip_format)
    imhover.renderers = []
    plot.add_tools(imhover)

    model_dict = {}

    for i, (label, sdf) in enumerate(split):

        # for the flux plot, we only show things that have a flux value
        df = sdf[sdf['hasflux']]

        key = f'obs{i}'
        model_dict[key] = plot.scatter(
            x='mjd',
            y='flux',
            color='color',
            marker='circle',
            fill_color='color',
            alpha='alpha',
            source=ColumnDataSource(df),
        )

        imhover.renderers.append(model_dict[key])

        key = f'bin{i}'
        model_dict[key] = plot.scatter(
            x='mjd',
            y='flux',
            color='color',
            marker='circle',
            fill_color='color',
            source=ColumnDataSource(
                data=dict(
                    mjd=[],
                    flux=[],
                    fluxerr=[],
                    filter=[],
                    color=[],
                    lim_mag=[],
                    mag=[],
                    magerr=[],
                    stacked=[],
                    instrument=[],
                )
            ),
        )

        imhover.renderers.append(model_dict[key])

        key = 'obserr' + str(i)
        y_err_x = []
        y_err_y = []

        for d, ro in df.iterrows():
            px = ro['mjd']
            py = ro['flux']
            err = ro['fluxerr']

            y_err_x.append((px, px))
            y_err_y.append((py - err, py + err))

        model_dict[key] = plot.multi_line(
            xs='xs',
            ys='ys',
            color='color',
            alpha='alpha',
            source=ColumnDataSource(
                data=dict(
                    xs=y_err_x, ys=y_err_y, color=df['color'], alpha=[1.0] * len(df)
                )
            ),
        )

        key = f'binerr{i}'
        model_dict[key] = plot.multi_line(
            xs='xs',
            ys='ys',
            color='color',
            source=ColumnDataSource(data=dict(xs=[], ys=[], color=[])),
        )

    plot.xaxis.axis_label = 'MJD'
    plot.yaxis.axis_label = 'Flux (μJy)'
    plot.toolbar.logo = None

    colors_labels = data[['color', 'label']].drop_duplicates()

    toggle = CheckboxWithLegendGroup(
        labels=colors_labels.label.tolist(),
        active=list(range(len(colors_labels))),
        colors=colors_labels.color.tolist(),
        width=width // 5,
    )

    # TODO replace `eval` with Namespaces
    # https://github.com/bokeh/bokeh/pull/6340
    toggle.js_on_click(
        CustomJS(
            args={'toggle': toggle, **model_dict},
            code=open(
                os.path.join(
                    os.path.dirname(__file__), '../static/js/plotjs', 'togglef.js'
                )
            ).read(),
        )
    )

    slider = Slider(
        start=0.0, end=15.0, value=0.0, step=1.0, title='Binsize (days)', max_width=350
    )

    callback = CustomJS(
        args={'slider': slider, 'toggle': toggle, **model_dict},
        code=open(
            os.path.join(os.path.dirname(__file__), '../static/js/plotjs', 'stackf.js')
        )
        .read()
        .replace('default_zp', str(PHOT_ZP))
        .replace('detect_thresh', str(PHOT_DETECTION_THRESHOLD)),
    )

    slider.js_on_change('value', callback)

    # Mark the first and last detections
    detection_dates = data[data['hasflux']]['mjd']
    if len(detection_dates) > 0:
        first = round(detection_dates.min(), 6)
        last = round(detection_dates.max(), 6)
        first_color = "#34b4eb"
        last_color = "#8992f5"
        midpoint = (upper + lower) / 2
        line_top = 5 * upper - 4 * midpoint
        line_bottom = 5 * lower - 4 * midpoint
        y = np.linspace(line_bottom, line_top, num=5000)
        first_r = plot.line(
            x=np.full(5000, first),
            y=y,
            line_alpha=0.5,
            line_color=first_color,
            line_width=2,
        )
        plot.add_tools(
            HoverTool(tooltips=[("First detection", f'{first}')], renderers=[first_r],)
        )
        last_r = plot.line(
            x=np.full(5000, last),
            y=y,
            line_alpha=0.5,
            line_color=last_color,
            line_width=2,
        )
        plot.add_tools(
            HoverTool(tooltips=[("Last detection", f'{last}')], renderers=[last_r],)
        )

    layout = column(slider, row(plot, toggle), sizing_mode='scale_width', width=width)

    p1 = Panel(child=layout, title='Flux')

    # now make the mag light curve
    ymax = (
        np.nanmax(
            (
                np.nanmax(data.loc[obsind, 'mag']) if any(obsind) else np.nan,
                np.nanmax(data.loc[~obsind, 'lim_mag']) if any(~obsind) else np.nan,
            )
        )
        + 0.1
    )
    ymin = (
        np.nanmin(
            (
                np.nanmin(data.loc[obsind, 'mag']) if any(obsind) else np.nan,
                np.nanmin(data.loc[~obsind, 'lim_mag']) if any(~obsind) else np.nan,
            )
        )
        - 0.1
    )

    xmin = data['mjd'].min() - 2
    xmax = data['mjd'].max() + 2

    plot = figure(
        aspect_ratio=1.5,
        sizing_mode='scale_both',
        active_drag='box_zoom',
        tools='box_zoom,wheel_zoom,pan,reset,save',
        y_range=(ymax, ymin),
        x_range=(xmin, xmax),
        toolbar_location='above',
        toolbar_sticky=False,
        x_axis_location='above',
    )

    # Mark the first and last detections again
    detection_dates = data[obsind]['mjd']
    if len(detection_dates) > 0:
        first = round(detection_dates.min(), 6)
        last = round(detection_dates.max(), 6)
        midpoint = (ymax + ymin) / 2
        line_top = 5 * ymax - 4 * midpoint
        line_bottom = 5 * ymin - 4 * midpoint
        y = np.linspace(line_bottom, line_top, num=5000)
        first_r = plot.line(
            x=np.full(5000, first),
            y=y,
            line_alpha=0.5,
            line_color=first_color,
            line_width=2,
        )
        plot.add_tools(
            HoverTool(tooltips=[("First detection", f'{first}')], renderers=[first_r],)
        )
        last_r = plot.line(
            x=np.full(5000, last),
            y=y,
            line_alpha=0.5,
            line_color=last_color,
            line_width=2,
        )
        plot.add_tools(
            HoverTool(
                tooltips=[("Last detection", f'{last}')],
                renderers=[last_r],
                point_policy='follow_mouse',
            )
        )

    imhover = HoverTool(tooltips=tooltip_format)
    imhover.renderers = []
    plot.add_tools(imhover)

    model_dict = {}

    for i, (label, df) in enumerate(split):

        key = f'obs{i}'
        model_dict[key] = plot.scatter(
            x='mjd',
            y='mag',
            color='color',
            marker='circle',
            fill_color='color',
            alpha='alpha',
            source=ColumnDataSource(df[df['obs']]),
        )

        imhover.renderers.append(model_dict[key])

        unobs_source = df[~df['obs']].copy()
        unobs_source.loc[:, 'alpha'] = 0.8

        key = f'unobs{i}'
        model_dict[key] = plot.scatter(
            x='mjd',
            y='lim_mag',
            color='color',
            marker='inverted_triangle',
            fill_color='white',
            line_color='color',
            alpha='alpha',
            source=ColumnDataSource(unobs_source),
        )

        imhover.renderers.append(model_dict[key])

        key = f'bin{i}'
        model_dict[key] = plot.scatter(
            x='mjd',
            y='mag',
            color='color',
            marker='circle',
            fill_color='color',
            source=ColumnDataSource(
                data=dict(
                    mjd=[],
                    flux=[],
                    fluxerr=[],
                    filter=[],
                    color=[],
                    lim_mag=[],
                    mag=[],
                    magerr=[],
                    instrument=[],
                    stacked=[],
                )
            ),
        )

        imhover.renderers.append(model_dict[key])

        key = 'obserr' + str(i)
        y_err_x = []
        y_err_y = []

        for d, ro in df[df['obs']].iterrows():
            px = ro['mjd']
            py = ro['mag']
            err = ro['magerr']

            y_err_x.append((px, px))
            y_err_y.append((py - err, py + err))

        model_dict[key] = plot.multi_line(
            xs='xs',
            ys='ys',
            color='color',
            alpha='alpha',
            source=ColumnDataSource(
                data=dict(
                    xs=y_err_x,
                    ys=y_err_y,
                    color=df[df['obs']]['color'],
                    alpha=[1.0] * len(df[df['obs']]),
                )
            ),
        )

        key = f'binerr{i}'
        model_dict[key] = plot.multi_line(
            xs='xs',
            ys='ys',
            color='color',
            source=ColumnDataSource(data=dict(xs=[], ys=[], color=[])),
        )

        key = f'unobsbin{i}'
        model_dict[key] = plot.scatter(
            x='mjd',
            y='lim_mag',
            color='color',
            marker='inverted_triangle',
            fill_color='white',
            line_color='color',
            alpha=0.8,
            source=ColumnDataSource(
                data=dict(
                    mjd=[],
                    flux=[],
                    fluxerr=[],
                    filter=[],
                    color=[],
                    lim_mag=[],
                    mag=[],
                    magerr=[],
                    instrument=[],
                    stacked=[],
                )
            ),
        )
        imhover.renderers.append(model_dict[key])

        key = f'all{i}'
        model_dict[key] = ColumnDataSource(df)

        key = f'bold{i}'
        model_dict[key] = ColumnDataSource(
            df[
                [
                    'mjd',
                    'flux',
                    'fluxerr',
                    'mag',
                    'magerr',
                    'filter',
                    'zp',
                    'magsys',
                    'lim_mag',
                    'stacked',
                ]
            ]
        )

    plot.xaxis.axis_label = 'MJD'
    plot.yaxis.axis_label = 'AB mag'
    plot.toolbar.logo = None

    obj = DBSession().query(Obj).get(obj_id)
    if obj.dm is not None:
        plot.extra_y_ranges = {
            "Absolute Mag": Range1d(start=ymax - obj.dm, end=ymin - obj.dm)
        }
        plot.add_layout(
            LinearAxis(y_range_name="Absolute Mag", axis_label="m - DM"), 'right'
        )

    now = Time.now().mjd
    plot.extra_x_ranges = {"Days Ago": Range1d(start=now - xmin, end=now - xmax)}
    plot.add_layout(LinearAxis(x_range_name="Days Ago", axis_label="Days Ago"), 'below')

    colors_labels = data[['color', 'label']].drop_duplicates()

    toggle = CheckboxWithLegendGroup(
        labels=colors_labels.label.tolist(),
        active=list(range(len(colors_labels))),
        colors=colors_labels.color.tolist(),
        width=width // 5,
    )

    # TODO replace `eval` with Namespaces
    # https://github.com/bokeh/bokeh/pull/6340
    toggle.js_on_click(
        CustomJS(
            args={'toggle': toggle, **model_dict},
            code=open(
                os.path.join(
                    os.path.dirname(__file__), '../static/js/plotjs', 'togglem.js'
                )
            ).read(),
        )
    )

    slider = Slider(start=0.0, end=15.0, value=0.0, step=1.0, title='Binsize (days)')

    button = Button(label="Export Bold Light Curve to CSV")
    button.js_on_click(
        CustomJS(
            args={'slider': slider, 'toggle': toggle, **model_dict},
            code=open(
                os.path.join(
                    os.path.dirname(__file__), '../static/js/plotjs', "download.js"
                )
            )
            .read()
            .replace('objname', obj_id)
            .replace('default_zp', str(PHOT_ZP)),
        )
    )

    toplay = row(slider, button)
    callback = CustomJS(
        args={'slider': slider, 'toggle': toggle, **model_dict},
        code=open(
            os.path.join(os.path.dirname(__file__), '../static/js/plotjs', 'stackm.js')
        )
        .read()
        .replace('default_zp', str(PHOT_ZP))
        .replace('detect_thresh', str(PHOT_DETECTION_THRESHOLD)),
    )
    slider.js_on_change('value', callback)

    layout = column(toplay, row(plot, toggle), sizing_mode='scale_width', width=width)

    p2 = Panel(child=layout, title='Mag')

    # now make period plot

    if obj.varstar:

        # get period from annotations (any for now)
        annotation_list = obj.get_annotations_readable_by(user)[0]
        if 'period' in annotation_list.data:
            period = annotation_list.data['period']
        else:
            period = 0.1

        period_xmin = -0.1
        period_xmax = 2.1

        period_plot = figure(
            aspect_ratio=1.7,
            sizing_mode='scale_both',
            active_drag='box_zoom',
            tools='box_zoom,wheel_zoom,pan,reset,save',
            y_range=(ymax, ymin),
            x_range=(period_xmin, period_xmax),
            toolbar_location='above',
            toolbar_sticky=False,
            x_axis_location='below',
        )

        period_plot.xaxis.axis_label = 'phase'
        period_plot.yaxis.axis_label = 'mag'
        period_plot.toolbar.logo = None

        obj = DBSession().query(Obj).get(obj_id)
        if obj.dm is not None:
            period_plot.extra_y_ranges = {
                "Absolute Mag": Range1d(start=ymax - obj.dm, end=ymin - obj.dm)
            }
            period_plot.add_layout(
                LinearAxis(y_range_name="Absolute Mag", axis_label="m - DM"), 'right'
            )

        period_imhover = HoverTool(tooltips=tooltip_format)
        period_imhover.renderers = []
        period_plot.add_tools(period_imhover)

        period_model_dict = {}

        for i, (label, df) in enumerate(split):

            df['mjd_folda'] = (df['mjd'] % period) / period
            df['mjd_foldb'] = df['mjd_folda'] + 1.0
            key = f'folda{i}'
            period_model_dict[key] = period_plot.scatter(
                x='mjd_folda',
                y='mag',
                color='color',
                marker='circle',
                fill_color='color',
                alpha='alpha',
                source=ColumnDataSource(df[df['obs']]),
            )

            period_imhover.renderers.append(period_model_dict[key])

            key = f'foldb{i}'
            period_model_dict[key] = period_plot.scatter(
                x='mjd_foldb',
                y='mag',
                color='color',
                marker='circle',
                fill_color='color',
                alpha='alpha',
                source=ColumnDataSource(df[df['obs']]),
            )
            period_imhover.renderers.append(period_model_dict[key])

            key = f'foldaerr{i}'
            y_err_x = []
            y_err_y = []

            for d, ro in df[df['obs']].iterrows():
                px = ro['mjd_folda']
                py = ro['mag']
                err = ro['magerr']

                y_err_x.append((px, px))
                y_err_y.append((py - err, py + err))

            period_model_dict[key] = period_plot.multi_line(
                xs='xs',
                ys='ys',
                color='color',
                alpha='alpha',
                source=ColumnDataSource(
                    data=dict(
                        xs=y_err_x,
                        ys=y_err_y,
                        color=df[df['obs']]['color'],
                        alpha=[1.0] * len(df[df['obs']]),
                    )
                ),
            )

            key = f'foldberr{i}'
            y_err_x = []
            y_err_y = []

            for d, ro in df[df['obs']].iterrows():
                px = ro['mjd_foldb']
                py = ro['mag']
                err = ro['magerr']

                y_err_x.append((px, px))
                y_err_y.append((py - err, py + err))

            period_model_dict[key] = period_plot.multi_line(
                xs='xs',
                ys='ys',
                color='color',
                alpha='alpha',
                source=ColumnDataSource(
                    data=dict(
                        xs=y_err_x,
                        ys=y_err_y,
                        color=df[df['obs']]['color'],
                        alpha=[1.0] * len(df[df['obs']]),
                    )
                ),
            )

            key = f'all{i}'
            period_model_dict[key] = ColumnDataSource(df[df['obs']])

        period_title = Div(text="Period (<i>days</i>): ")
        period_slider = Slider(
            value=period if period is not None else 0.0,
            start=0.0,
            end=3.0,
            step=0.0000001,
            show_value=True,
            format="0[.]0000000",
        )
        period_textinput = TextInput(value=str(period if period is not None else 0.0))
        period_textinput.js_on_change(
            'value',
            CustomJS(
                args={'period': period_textinput, 'slider': period_slider},
                code="""
                // Update slider value to match text input
                slider.value = parseFloat(period.value).toFixed(7);
            """,
            ),
        )
        period_slider.js_on_change(
            'value',
            CustomJS(
                args={
                    'slider': period_slider,
                    'textinput': period_textinput,
                    'toggle': toggle,
                    **period_model_dict,
                },
                code="""
                const period = parseFloat(slider.value).toFixed(7);
                textinput.value = parseFloat(slider.value).toFixed(7);
                textinput.change.emit();
                for (let i = 0; i < toggle.labels.length; i++) {
                    const allsource = eval(`all${i}`);
                    const mjd = allsource.data.mjd;
                    const folda = eval(`folda${i}`).data_source;
                    const foldb = eval(`foldb${i}`).data_source;
                    for (let m = 0; m < mjd.length; m++) {
                        folda.data.mjd_folda[m] = (mjd[m] % period) / period;
                        foldb.data.mjd_foldb[m] = folda.data.mjd_folda[m] + 1.;
                    }
                    folda.change.emit();
                    foldb.change.emit();
                }
            """,
            ),
        )
        period_button = Button(label="Reset Period")
        period_button.js_on_click(
            CustomJS(
                args={
                    'slider': period_slider,
                    'textinput': period_textinput,
                    'period': period,
                },
                code="""
                    textinput.value = parseFloat(period).toFixed(13);
                    slider.value = period;
                """,
            )
        )

        period_toggle = CheckboxWithLegendGroup(
            labels=colors_labels.label.tolist(),
            active=list(range(len(colors_labels))),
            colors=colors_labels.color.tolist(),
            width=width // 5,
        )

        # TODO replace `eval` with Namespaces
        # https://github.com/bokeh/bokeh/pull/6340
        period_toggle.js_on_click(
            CustomJS(
                args={'toggle': period_toggle, **period_model_dict},
                code=open(
                    os.path.join(
                        os.path.dirname(__file__), '../static/js/plotjs', 'togglep.js'
                    )
                ).read(),
            )
        )
        period_row = row(period_slider, period_button)
        period_column = column(period_title, period_row, period_textinput)

        period_layout = column(
            row(period_column),
            row(period_plot, period_toggle),
            sizing_mode='scale_width',
            width=width,
        )

        p3 = Panel(child=period_layout, title='Period')

        tabs = Tabs(tabs=[p2, p1, p3], width=width, height=height, sizing_mode='fixed')
    else:
        tabs = Tabs(tabs=[p2, p1], width=width, height=height, sizing_mode='fixed')
    return bokeh_embed.json_item(tabs)


def spectroscopy_plot(obj_id, user, spec_id=None, width=600, height=300):
    obj = Obj.query.get(obj_id)
    spectra = (
        DBSession()
        .query(Spectrum)
        .join(Obj)
        .join(GroupSpectrum)
        .filter(
            Spectrum.obj_id == obj_id,
            GroupSpectrum.group_id.in_([g.id for g in user.accessible_groups]),
        )
    ).all()

    if spec_id is not None:
        spectra = [spec for spec in spectra if spec.id == int(spec_id)]
    if len(spectra) == 0:
        return None, None, None

    rainbow = cm.get_cmap('rainbow', len(spectra))
    palette = list(map(rgb2hex, rainbow(range(len(spectra)))))
    color_map = dict(zip([s.id for s in spectra], palette))

    data = []
    for i, s in enumerate(spectra):

        # normalize spectra to a median flux of 1 for easy comparison
        normfac = np.nanmedian(np.abs(s.fluxes))
        normfac = normfac if normfac != 0.0 else 1e-20

        df = pd.DataFrame(
            {
                'wavelength': s.wavelengths,
                'flux': s.fluxes / normfac,
                'id': s.id,
                'telescope': s.instrument.telescope.name,
                'instrument': s.instrument.name,
                'date_observed': s.observed_at.date().isoformat(),
                'pi': (
                    s.assignment.run.pi
                    if s.assignment is not None
                    else (
                        s.followup_request.allocation.pi
                        if s.followup_request is not None
                        else ""
                    )
                ),
            }
        )
        data.append(df)
    data = pd.concat(data)

    dfs = []
    for i, s in enumerate(spectra):
        # Smooth the spectrum by using a rolling average
        df = (
            pd.DataFrame({'wavelength': s.wavelengths, 'flux': s.fluxes})
            .rolling(2)
            .mean(numeric_only=True)
            .dropna()
        )
        dfs.append(df)

    smoothed_data = pd.concat(dfs)

    split = data.groupby('id')
    hover = HoverTool(
        tooltips=[
            ('wavelength', '@wavelength{0,0.000}'),
            ('flux', '@flux'),
            ('telesecope', '@telescope'),
            ('instrument', '@instrument'),
            ('UTC date observed', '@date_observed'),
            ('PI', '@pi'),
        ]
    )
    smoothed_max = np.max(smoothed_data['flux'])
    smoothed_min = np.min(smoothed_data['flux'])
    ymax = smoothed_max * 1.05
    ymin = smoothed_min - 0.05 * (smoothed_max - smoothed_min)
    xmin = np.min(data['wavelength']) - 100
    xmax = np.max(data['wavelength']) + 100
    if obj.redshift is not None and obj.redshift > 0:
        xmin_rest = xmin / (1.0 + obj.redshift)
        xmax_rest = xmax / (1.0 + obj.redshift)
    plot = figure(
        aspect_ratio=1.5,
        sizing_mode='scale_width',
        y_range=(ymin, ymax),
        x_range=(xmin, xmax),
        tools='box_zoom,wheel_zoom,pan,reset',
        active_drag='box_zoom',
    )
    plot.add_tools(hover)
    model_dict = {}
    for i, (key, df) in enumerate(split):
        model_dict['s' + str(i)] = plot.step(
            x='wavelength', y='flux', color=color_map[key], source=ColumnDataSource(df),
        )
        model_dict['l' + str(i)] = plot.line(
            x='wavelength',
            y='flux',
            color=color_map[key],
            source=ColumnDataSource(df),
            line_alpha=0.0,
        )
    plot.xaxis.axis_label = 'Wavelength (Å)'
    plot.yaxis.axis_label = 'Flux'
    plot.toolbar.logo = None
    if obj.redshift is not None and obj.redshift > 0:
        plot.extra_x_ranges = {"rest_wave": Range1d(start=xmin_rest, end=xmax_rest)}
        plot.add_layout(
            LinearAxis(x_range_name="rest_wave", axis_label="Rest Wavelength (Å)"),
            'above',
        )

    # TODO how to choose a good default?
    plot.y_range = Range1d(0, 1.03 * data.flux.max())

    spec_labels = []
    for k, _ in split:
        s = Spectrum.query.get(k)
        label = f'{s.instrument.telescope.nickname}/{s.instrument.name} ({s.observed_at.date().isoformat()})'
        spec_labels.append(label)

    toggle = CheckboxWithLegendGroup(
        labels=spec_labels,
        active=list(range(len(spectra))),
        colors=[color_map[k] for k, df in split],
        width=width // 5,
    )
    toggle.js_on_click(
        CustomJS(
            args={'toggle': toggle, **model_dict},
            code="""
          for (let i = 0; i < toggle.labels.length; i++) {
              eval("s" + i).visible = (toggle.active.includes(i))
          }
    """,
        ),
    )

    z_title = Div(text="Redshift (<i>z</i>): ")
    z_slider = Slider(
        value=obj.redshift if obj.redshift is not None else 0.0,
        start=0.0,
        end=3.0,
        step=0.001,
        show_value=False,
        format="0[.]000",
    )
    z_textinput = TextInput(
        value=str(obj.redshift if obj.redshift is not None else 0.0)
    )
    z_slider.js_on_change(
        'value',
        CustomJS(
            args={'slider': z_slider, 'textinput': z_textinput},
            code="""
            textinput.value = parseFloat(slider.value).toFixed(3);
            textinput.change.emit();
        """,
        ),
    )
    z = column(z_title, z_slider, z_textinput)

    v_title = Div(text="<i>V</i><sub>expansion</sub> (km/s): ")
    v_exp_slider = Slider(value=0.0, start=0.0, end=3e4, step=10.0, show_value=False,)
    v_exp_textinput = TextInput(value='0')
    v_exp_slider.js_on_change(
        'value',
        CustomJS(
            args={'slider': v_exp_slider, 'textinput': v_exp_textinput},
            code="""
            textinput.value = parseFloat(slider.value).toFixed(0);
            textinput.change.emit();
        """,
        ),
    )
    v_exp = column(v_title, v_exp_slider, v_exp_textinput)

    for i, (wavelengths, color) in enumerate(SPEC_LINES.values()):
        el_data = pd.DataFrame({'wavelength': wavelengths})
        obj_redshift = 0 if obj.redshift is None else obj.redshift
        el_data['x'] = el_data['wavelength'] * (1.0 + obj_redshift)
        model_dict[f'el{i}'] = plot.segment(
            x0='x',
            x1='x',
            # TODO change limits
            y0=0,
            y1=1e4,
            color=color,
            source=ColumnDataSource(el_data),
        )
        model_dict[f'el{i}'].visible = False

    # Split spectral line legend into columns
    columns = 7
    element_dicts = zip(*itertools.zip_longest(*[iter(SPEC_LINES.items())] * columns))

    elements_groups = []  # The Bokeh checkbox groups
    callbacks = []  # The checkbox callbacks for each element
    for column_idx, element_dict in enumerate(element_dicts):
        element_dict = [e for e in element_dict if e is not None]
        labels = [key for key, value in element_dict]
        colors = [c for key, (w, c) in element_dict]
        elements = CheckboxWithLegendGroup(
            labels=labels, active=[], colors=colors, width=width // (columns + 1)
        )
        elements_groups.append(elements)

        callback = CustomJS(
            args={
                'elements': elements,
                'z': z_textinput,
                'v_exp': v_exp_textinput,
                **model_dict,
            },
            code=f"""
            let c = 299792.458; // speed of light in km / s
            const i_max = {column_idx} +  {columns} * elements.labels.length;
            let local_i = 0;
            for (let i = {column_idx}; i < i_max; i = i + {columns}) {{
                let el = eval("el" + i);
                el.visible = (elements.active.includes(local_i))
                el.data_source.data.x = el.data_source.data.wavelength.map(
                    x_i => (x_i * (1 + parseFloat(z.value)) /
                                    (1 + parseFloat(v_exp.value) / c))
                );
                el.data_source.change.emit();
                local_i++;
            }}
        """,
        )
        elements.js_on_click(callback)
        callbacks.append(callback)

    z_textinput.js_on_change(
        'value',
        CustomJS(
            args={
                'z': z_textinput,
                'slider': z_slider,
                'v_exp': v_exp_textinput,
                **model_dict,
            },
            code="""
            // Update slider value to match text input
            slider.value = parseFloat(z.value).toFixed(3);
        """,
        ),
    )

    v_exp_textinput.js_on_change(
        'value',
        CustomJS(
            args={
                'z': z_textinput,
                'slider': v_exp_slider,
                'v_exp': v_exp_textinput,
                **model_dict,
            },
            code="""
            // Update slider value to match text input
            slider.value = parseFloat(v_exp.value).toFixed(3);
        """,
        ),
    )

    # Update the element spectral lines as well
    for callback in callbacks:
        z_textinput.js_on_change('value', callback)
        v_exp_textinput.js_on_change('value', callback)

    row1 = row(plot, toggle)
    row2 = row(elements_groups)
    row3 = row(z, v_exp)
    layout = column(row1, row2, row3, width=width)
    return bokeh_embed.json_item(layout)
