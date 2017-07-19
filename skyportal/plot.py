import numpy as np
import pandas as pd

from bokeh.core.json_encoder import serialize_json
from bokeh.document import Document
from bokeh.layouts import row
from bokeh.models import CustomJS, Whisker, DatetimeTickFormatter, HoverTool
from bokeh.models.widgets import CheckboxGroup
from bokeh.palettes import viridis
from bokeh.plotting import figure, show, ColumnDataSource
from bokeh.util.serialization import make_id

from skyportal.models import (DBSession, Source, Photometry, Spectrum,
                              Instrument, Telescope)


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

    return docs_json, render_items


def photometry_plot(source_id):
    """Create scatter plot of photometry for source.

    Parameters
    ----------
    source_id : int
        ID of source to be plotted.

    Returns
    -------
    (str, str)
        Returns (docs_json, render_items) json for the desired plot.
    """
    color_map = {'ipr': 'yellow', 'rpr': 'red', 'g': 'green'}

    data = pd.read_sql(DBSession().query(Photometry,
                                         Telescope.nickname.label('telescope'))
                           .join(Instrument).join(Telescope)
                           .filter(Photometry.source_id == source_id)
                           .statement, DBSession().bind)
    if data.empty:
        return None, None

    for col in ['mag', 'e_mag', 'lim_mag']:
        data.loc[data[col] > 90, col] = np.nan
    data['color'] = [color_map[f] for f in data['filter']]
    data['label'] = [f'{t} {f}-band'
                     for t, f in zip(data['telescope'], data['filter'])]
    data['observed'] = ~np.isnan(data.mag)
    split = data.groupby(('label', 'observed'))

    plot = figure(plot_width=600, plot_height=300, active_drag='box_zoom',
                  tools='box_zoom,pan,reset',
                  y_range=(np.nanmax(data['mag']) + 0.1,
                           np.nanmin(data['mag']) - 0.1))
    model_dict = {}
    for i, ((label, is_obs), df) in enumerate(split):
        key = ("" if is_obs else "un") + 'obs' + str(i // 2)
        model_dict[key] = plot.scatter(x='obs_time', y='mag' if is_obs else 'lim_mag',
                                       color='color',
                                       marker='circle' if is_obs else 'inverted_triangle',
                                       fill_color='color' if is_obs else 'white',
                                       source=ColumnDataSource(df))
    plot.xaxis.axis_label = 'Observation Date'
    plot.xaxis.formatter = DatetimeTickFormatter(hours=['%D'], days=['%D'],
                                                 months=['%D'], years=['%D'])

    hover = HoverTool(tooltips=[('obs_time', '@obs_time{%D}'), ('mag', '@mag'),
                                ('lim_mag', '@lim_mag'),
                                ('filter', '@filter')],
                      formatters={'obs_time': 'datetime'})
    plot.add_tools(hover)

    checkbox = CheckboxGroup(labels=list(data.label.unique()),
                             active=list(range(len(data.label.unique()))))
    checkbox.callback = CustomJS(args={'checkbox': checkbox, **model_dict},
                                 code="""
        for (let i = 0; i < checkbox.labels.length; i++) {
            eval("obs" + i).visible = (checkbox.active.includes(i))
            eval("unobs" + i).visible = (checkbox.active.includes(i));
        }
    """)

    layout = row(plot, checkbox)

    return _plot_to_json(layout)


def spectroscopy_plot(source_id):
    spectra = Source.query.get(source_id).spectra
    color_map = dict(zip([s.id for s in spectra], viridis(len(spectra))))
    data = pd.concat([pd.DataFrame({'wavelength': s.wavelengths,
                                    'flux': s.fluxes, 'id': s.id,
                                    'instrument': s.instrument.telescope.nickname})
                      for i, s in enumerate(spectra)])
    split = data.groupby('id')
    hover = HoverTool(tooltips=[('wavelength', '$x'), ('flux', '$y'),
                                ('instrument', '@instrument')])
    plot = figure(plot_width=600, plot_height=300,
               tools='box_zoom,pan,reset', active_drag='box_zoom')
    plot.add_tools(hover)
    model_dict = {}
    for i, (key, df) in enumerate(split):
        model_dict['s' + str(i)] = plot.line(x='wavelength', y='flux',
                                             color=color_map[key],
                                             source=ColumnDataSource(df))
    plot.xaxis.axis_label = 'Wavelength (Å)'
    plot.yaxis.axis_label = 'Flux'
    checkbox = CheckboxGroup(labels=[s.instrument.telescope.nickname for s in spectra],
                             active=list(range(len(spectra))))
    checkbox.callback = CustomJS(args={'checkbox': checkbox, **model_dict},
                                 code="""
          console.log(checkbox.active);
          for (let i = 0; i < checkbox.labels.length; i++) {
              eval("s" + i).visible = (checkbox.active.includes(i))
          }
    """)
    layout = row(plot, checkbox)

    return _plot_to_json(layout)
