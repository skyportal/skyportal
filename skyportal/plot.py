import numpy as np
import pandas as pd

from bokeh.core.json_encoder import serialize_json
from bokeh.core.properties import List, String
from bokeh.document import Document
from bokeh.layouts import row, column
from bokeh.models import CustomJS, HoverTool, Range1d, Slider, Button
from bokeh.models.widgets import CheckboxGroup, TextInput, Panel, Tabs
from bokeh.palettes import viridis
from bokeh.plotting import figure, ColumnDataSource
from bokeh.util.compiler import bundle_all_models
from bokeh.util.serialization import make_id

from matplotlib import cm
from matplotlib.colors import rgb2hex

import os
from skyportal.models import (DBSession, Obj, Photometry,
                              Instrument, Telescope, PHOT_ZP)

import sncosmo
from sncosmo.photdata import PhotometricData
from astropy.table import Table


DETECT_THRESH = 5  # sigma

SPEC_LINES = {
    'H': ([3970, 4102, 4341, 4861, 6563], '#ff0000'),
    'He': ([3886, 4472, 5876, 6678, 7065], '#002157'),
    'He II': ([3203, 4686], '#003b99'),
    'C II': ([3919, 4267, 6580, 7234, 9234], '#570199'),
    'C III': ([4650, 5696], '#a30198'),
    'C IV': ([5801], '#ff0073'),
    'O': ([7772, 7774, 7775, 8447, 9266], '#007236'),
    'O II': ([3727], '#00a64d'),
    'O III': ([4959, 5007], '#00bf59'),
    'Na': ([5890, 5896, 8183, 8195], '#aba000'),
    'Mg': ([2780, 2852, 3829, 3832, 3838, 4571, 5167, 5173, 5184], '#8c6239'),
    'Mg II': ([2791, 2796, 2803, 4481], '#bf874e'),
    'Si II': ([3856, 5041, 5056, 5670, 6347, 6371], '#5674b9'),
    'S II': ([5433, 5454, 5606, 5640, 5647, 6715], '#a38409'),
    'Ca II': ([3934, 3969, 7292, 7324, 8498, 8542, 8662], '#005050'),
    'Fe II': ([5018, 5169], '#f26c4f'),
    'Fe III': ([4397, 4421, 4432, 5129, 5158], '#f9917b')
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
    __implementation__ = """
import {empty, input, label, div} from "core/dom"
import * as p from "core/properties"
import {CheckboxGroup, CheckboxGroupView} from "models/widgets/checkbox_group"
export class CheckboxWithLegendGroupView extends CheckboxGroupView
  render: () ->
    super()
    empty(@el)
    active = @model.active
    colors = @model.colors
    for text, i in @model.labels
      inputEl = input({type: "checkbox", value: "#{i}"})
      inputEl.addEventListener("change", () => @change_input())
      if @model.disabled then inputEl.disabled = true
      if i in active then inputEl.checked = true
      attrs = {
        style: "border-left: 12px solid #{colors[i]}; padding-left: 0.3em;"
      }
      labelEl = label(attrs, inputEl, text)
      if @model.inline
        labelEl.classList.add("bk-bs-checkbox-inline")
        @el.appendChild(labelEl)
      else
        divEl = div({class: "bk-bs-checkbox"}, labelEl)
        @el.appendChild(divEl)
    return @
export class CheckboxWithLegendGroup extends CheckboxGroup
  type: "CheckboxWithLegendGroup"
  default_view: CheckboxWithLegendGroupView
  @define {
    colors:   [ p.Array, []    ]
  }
"""


# TODO replace with (script, div) method
def _plot_to_json(plot):
    """Convert plot to JSON objects necessary for rendering with `bokehJS`.
    Parameters
    ----------
    plot : bokeh.plotting.figure.Figure
        Bokeh plot object to be rendered.
    Returns
    -------
    (str, str)
        Returns (docs_json, render_items) json for the desired plot.
    """
    render_items = [{'docid': plot._id, 'elementid': make_id()}]

    doc = Document()
    doc.add_root(plot)
    docs_json_inner = doc.to_json()
    docs_json = {render_items[0]['docid']: docs_json_inner}

    docs_json = serialize_json(docs_json)
    render_items = serialize_json(render_items)
    custom_model_js = bundle_all_models()

    return docs_json, render_items, custom_model_js


tooltip_format = [('mjd', '@mjd{0.000000}'),
                  ('flux', '@flux'),
                  ('filter', '@filter'),
                  ('fluxerr', '@fluxerr'),
                  ('mag', '@mag'),
                  ('magerr', '@magerr'),
                  ('lim_mag', '@lim_mag'),
                  ('instrument', '@instrument'),
                  ('stacked', '@stacked')]
cmap = cm.get_cmap('jet_r')


def get_color(bandpass_name, cmap_limits=(3000., 10000.)):
    if bandpass_name.startswith('ztf'):
        return {'ztfg': 'green', 'ztfi': 'orange', 'ztfr': 'red'}[bandpass_name]
    else:
        bandpass = sncosmo.get_bandpass(bandpass_name)
        wave = bandpass.wave_eff
        rgb = cmap((cmap_limits[1] - wave) /
                   (cmap_limits[1] - cmap_limits[0])
                   )[:3]
        bandcolor = rgb2hex(rgb)

        return bandcolor


# TODO make async so that thread isn't blocked
def photometry_plot(obj_id, width=600, height=300):
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

    data = pd.read_sql(DBSession()
                       .query(Photometry, Telescope.nickname.label('telescope'),
                              Instrument.name.label('instrument'))
                       .join(Instrument).join(Telescope)
                       .filter(Photometry.obj_id == obj_id)
                       .statement, DBSession().bind)
    if data.empty:
        return None, None, None

    data['color'] = [get_color(f) for f in data['filter']]
    data['label'] = [f'{i} {f}-band' for i, f in zip(data['instrument'],
                                                     data['filter'])]

    data['zp'] = PHOT_ZP
    data['magsys'] = 'ab'
    data['alpha'] = 1.
    data['lim_mag'] = -2.5 * np.log10(data['fluxerr'] * DETECT_THRESH) + data['zp']

    # Passing a dictionary to a bokeh datasource causes the frontend to die, 
    # deleting the dictionary column fixes that 
    del data['original_user_data']

    # keep track of things that are only upper limits
    data['hasflux'] = ~data['flux'].isna()

    # calculate the magnitudes - a photometry point is considered "significant"
    # or "detected" (and thus can be represented by a magnitude) if its snr
    # is above DETECT_THRESH
    obsind = data['hasflux'] & (data['flux'].fillna(0.) / data['fluxerr'] >= DETECT_THRESH)
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

    # show middle 98% of data
    finite = np.isfinite(data['flux'])
    fdata = data[finite]
    lower = np.percentile(fdata['flux'], 1.)
    upper = np.percentile(fdata['flux'], 99.)

    lower -= np.abs(lower) * 0.1
    upper += np.abs(upper) * 0.1

    plot = figure(
        plot_width=width,
        plot_height=height,
        active_drag='box_zoom',
        tools='box_zoom,wheel_zoom,pan,reset,save',
        y_range=(lower, upper)
    )

    imhover = HoverTool(tooltips=tooltip_format)
    plot.add_tools(imhover)

    model_dict = {}

    for i, (label, sdf) in enumerate(split):

        # for the flux plot, we only show things that have a flux value
        df = sdf[sdf['hasflux']]

        key = f'obs{i}'
        model_dict[key] = plot.scatter(
            x='mjd', y='flux',
            color='color',
            marker='circle',
            fill_color='color',
            alpha='alpha',
            source=ColumnDataSource(df),
        )

        imhover.renderers.append(model_dict[key])

        key = f'bin{i}'
        model_dict[key] = plot.scatter(
            x='mjd', y='flux',
            color='color',
            marker='circle',
            fill_color='color',
            source=ColumnDataSource(data=dict(mjd=[], flux=[], fluxerr=[],
                                              filter=[], color=[], lim_mag=[],
                                              mag=[], magerr=[], stacked=[],
                                              instrument=[]))
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
            xs='xs', ys='ys', color='color', alpha='alpha',
            source=ColumnDataSource(data=dict(xs=y_err_x, ys=y_err_y,
                                              color=df['color'],
                                              alpha=[1.] * len(df)))
        )

        key = f'binerr{i}'
        model_dict[key] = plot.multi_line(
            xs='xs', ys='ys', color='color',
            source=ColumnDataSource(data=dict(xs=[], ys=[], color=[]))
        )

    plot.xaxis.axis_label = 'MJD'
    plot.yaxis.axis_label = 'Flux (μJy)'
    plot.toolbar.logo = None


    toggle = CheckboxWithLegendGroup(
        labels=list(data.label.unique()),
        active=list(range(len(data.label.unique()))),
        colors=list(data.color.unique()))

    # TODO replace `eval` with Namespaces
    # https://github.com/bokeh/bokeh/pull/6340
    toggle.callback = CustomJS(args={'toggle': toggle, **model_dict},
                               code=open(os.path.join(os.path.dirname(__file__),
                                                      '../static/js/plotjs',
                                                      'togglef.js')
                                         ).read())

    slider = Slider(
        start=0., end=15., value=0., step=1., title='binsize (days)'
    )

    callback = CustomJS(args={'slider': slider, 'toggle': toggle, **model_dict},
                        code=open(os.path.join(os.path.dirname(__file__),
                                               '../static/js/plotjs',
                                               'stackf.js')).read().replace(
                                   'default_zp', str(PHOT_ZP)
                               ).replace(
                                   'detect_thresh', str(DETECT_THRESH)
                               )
                        )

    slider.js_on_change('value', callback)

    layout = row(plot, toggle)
    layout = column(slider, layout)

    p1 = Panel(child=layout, title='Flux')

    # now make the mag light curve
    ymax = 1.1 * data['lim_mag']
    ymin = 0.9 * data['lim_mag']

    if len(data['obs']) > 0:
        ymax[data['obs']] = (data['mag'] + data['magerr']) * 1.1
        ymin[data['obs']] = (data['mag'] - data['magerr']) * 0.9

    plot = figure(
        plot_width=width,
        plot_height=height,
        active_drag='box_zoom',
        tools='box_zoom,wheel_zoom,pan,reset,save',
        y_range=(np.nanmax(ymax), np.nanmin(ymin)),
        toolbar_location='above'
    )

    imhover = HoverTool(tooltips=tooltip_format)
    plot.add_tools(imhover)

    model_dict = {}

    for i, (label, df) in enumerate(split):

        key = f'obs{i}'
        model_dict[key] = plot.scatter(
            x='mjd', y='mag',
            color='color',
            marker='circle',
            fill_color='color',
            alpha='alpha',
            source=ColumnDataSource(df[df['obs']])
        )

        imhover.renderers.append(model_dict[key])

        unobs_source = df[~df['obs']].copy()
        unobs_source.loc[:, 'alpha'] = 0.8

        key = f'unobs{i}'
        model_dict[key] = plot.scatter(
            x='mjd', y='lim_mag',
            color='color',
            marker='inverted_triangle',
            fill_color='white',
            line_color='color',
            alpha='alpha',
            source=ColumnDataSource(unobs_source)
        )

        imhover.renderers.append(model_dict[key])

        key = f'bin{i}'
        model_dict[key] = plot.scatter(
            x='mjd', y='mag',
            color='color',
            marker='circle',
            fill_color='color',
            source=ColumnDataSource(data=dict(mjd=[], flux=[], fluxerr=[],
                                              filter=[], color=[], lim_mag=[],
                                              mag=[], magerr=[], instrument=[],
                                              stacked=[]))
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
            xs='xs', ys='ys', color='color', alpha='alpha',
            source=ColumnDataSource(data=dict(xs=y_err_x, ys=y_err_y,
                                              color=df[df['obs']]['color'],
                                              alpha=[1.] * len(df[df['obs']])))
        )

        key = f'binerr{i}'
        model_dict[key] = plot.multi_line(
            xs='xs', ys='ys', color='color',
            source=ColumnDataSource(data=dict(xs=[], ys=[], color=[]))
        )

        key = f'unobsbin{i}'
        model_dict[key] = plot.scatter(
            x='mjd', y='lim_mag',
            color='color',
            marker='inverted_triangle',
            fill_color='white',
            line_color='color',
            alpha=0.8,
            source=ColumnDataSource(data=dict(mjd=[], flux=[], fluxerr=[],
                                              filter=[], color=[], lim_mag=[],
                                              mag=[], magerr=[], instrument=[],
                                              stacked=[]))
        )
        imhover.renderers.append(model_dict[key])

        key = f'all{i}'
        model_dict[key] = ColumnDataSource(df)

        key = f'bold{i}'
        model_dict[key] = ColumnDataSource(df[['mjd', 'flux', 'fluxerr','mag',
                                               'magerr', 'filter', 'zp',
                                               'magsys', 'lim_mag', 'stacked']])

    plot.xaxis.axis_label = 'MJD'
    plot.yaxis.axis_label = 'AB mag'
    plot.toolbar.logo = None

    toggle = CheckboxWithLegendGroup(
        labels=list(data.label.unique()),
        active=list(range(len(data.label.unique()))),
        colors=list(data.color.unique()))

    # TODO replace `eval` with Namespaces
    # https://github.com/bokeh/bokeh/pull/6340
    toggle.callback = CustomJS(
        args={'toggle': toggle, **model_dict},
        code=open(os.path.join(os.path.dirname(__file__),
                               '../static/js/plotjs', 'togglem.js')
                  ).read()
    )

    slider = Slider(
        start=0., end=15., value=0., step=1., title='Binsize (days)'
    )

    button = Button(label="Export Bold Light Curve to CSV")
    button.callback = CustomJS(
        args={'slider': slider, 'toggle': toggle, **model_dict},
        code=open(os.path.join(
            os.path.dirname(__file__),
            '../static/js/plotjs',
            "download.js")).read().replace(
            'objname', obj_id
        ).replace('default_zp', str(PHOT_ZP)))

    toplay = row(slider, button)
    callback = CustomJS(args={'slider': slider, 'toggle': toggle, **model_dict},
                        code=open(os.path.join(os.path.dirname(__file__),
                                               '../static/js/plotjs',
                                               'stackm.js')).read().replace(
                                   'default_zp', str(PHOT_ZP)
                               ).replace(
                                   'detect_thresh', str(DETECT_THRESH)
                               ))
    slider.js_on_change('value', callback)

    layout = row(plot, toggle)
    layout = column(toplay, layout)

    p2 = Panel(child=layout, title='Mag')

    tabs = Tabs(tabs=[p2, p1])
    return _plot_to_json(tabs)


# TODO make async so that thread isn't blocked
def spectroscopy_plot(obj_id):
    """TODO normalization? should this be handled at data ingestion or plot-time?"""
    obj = Obj.query.get(obj_id)
    spectra = Obj.query.get(obj_id).spectra
    if len(spectra) == 0:
        return None, None, None

    color_map = dict(zip([s.id for s in spectra], viridis(len(spectra))))
    data = pd.concat(
        [pd.DataFrame({'wavelength': s.wavelengths,
                       'flux': s.fluxes, 'id': s.id,
                       'instrument': s.instrument.telescope.nickname})
         for i, s in enumerate(spectra)]
    )
    split = data.groupby('id')
    hover = HoverTool(tooltips=[('wavelength', '$x'), ('flux', '$y'),
                                ('instrument', '@instrument')])
    plot = figure(plot_width=600, plot_height=300, sizing_mode='scale_both',
                  tools='box_zoom,wheel_zoom,pan,reset',
                  active_drag='box_zoom')
    plot.add_tools(hover)
    model_dict = {}
    for i, (key, df) in enumerate(split):
        model_dict['s' + str(i)] = plot.line(x='wavelength', y='flux',
                                             color=color_map[key],
                                             source=ColumnDataSource(df))
    plot.xaxis.axis_label = 'Wavelength (Å)'
    plot.yaxis.axis_label = 'Flux'
    plot.toolbar.logo = None

    # TODO how to choose a good default?
    plot.y_range = Range1d(0, 1.03 * data.flux.max())

    toggle = CheckboxWithLegendGroup(labels=[s.instrument.telescope.nickname
                                             for s in spectra],
                                     active=list(range(len(spectra))),
                                     width=100,
                                     colors=[color_map[k] for k, df in split])
    toggle.callback = CustomJS(args={'toggle': toggle, **model_dict},
                               code="""
          for (let i = 0; i < toggle.labels.length; i++) {
              eval("s" + i).visible = (toggle.active.includes(i))
          }
    """)

    elements = CheckboxWithLegendGroup(
        labels=list(SPEC_LINES.keys()),
        active=[], width=80,
        colors=[c for w, c in SPEC_LINES.values()]
    )
    z = TextInput(value=str(obj.redshift), title="z:")
    v_exp = TextInput(value='0', title="v_exp:")
    for i, (wavelengths, color) in enumerate(SPEC_LINES.values()):
        el_data = pd.DataFrame({'wavelength': wavelengths})
        el_data['x'] = el_data['wavelength'] * (1 + obj.redshift)
        model_dict[f'el{i}'] = plot.segment(x0='x', x1='x',
                                            # TODO change limits
                                            y0=0, y1=1e-13, color=color,
                                            source=ColumnDataSource(el_data))
        model_dict[f'el{i}'].visible = False

    # TODO callback policy: don't require submit for text changes?
    elements.callback = CustomJS(args={'elements': elements, 'z': z,
                                       'v_exp': v_exp, **model_dict},
                                 code="""
          let c = 299792.458; // speed of light in km / s
          for (let i = 0; i < elements.labels.length; i++) {
              let el = eval("el" + i);
              el.visible = (elements.active.includes(i))
              el.data_source.data.x = el.data_source.data.wavelength.map(
                  x_i => (x_i * (1 + parseFloat(z.value)) /
                                (1 + parseFloat(v_exp.value) / c))
              );
              el.data_source.change.emit();
          }
    """)
    z.callback = elements.callback
    v_exp.callback = elements.callback

    layout = row(plot, toggle, elements, column(z, v_exp))
    return _plot_to_json(layout)
