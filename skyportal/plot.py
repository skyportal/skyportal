import numpy as np
import pandas as pd

from bokeh.core.json_encoder import serialize_json
from bokeh.document import Document
from bokeh.models import Whisker, DatetimeTickFormatter, HoverTool
from bokeh.plotting import figure, show, ColumnDataSource
from bokeh.util.serialization import make_id

from skyportal.models import DBSession, Source, Photometry, Spectrum


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

    data = pd.read_sql(Photometry
                           .query
                           .filter(Photometry.source_id == source_id)
                           .statement, DBSession().bind)
    if data.empty:
        return None, None

    # TODO this feels redundant and silly but I couldn't figure out a one-liner
    data.loc[data.mag > 90, 'mag'] = np.nan
    data.loc[data.e_mag > 90, 'e_mag'] = np.nan
    data.loc[data.lim_mag > 90, 'lim_mag'] = np.nan
    data['min'] = data.mag + data.e_mag
    data['max'] = data.mag - data.e_mag
    data['color'] = [color_map[f] for f in data['filter']]

    observed = ColumnDataSource(data.loc[np.isnan(data.lim_mag), :])
    unobserved = ColumnDataSource(data.loc[np.isnan(data.mag), :])

    hover = HoverTool(tooltips=[('obs_time', '@obs_time{%D}'), ('mag', '@mag'),
                                ('lim_mag', '@lim_mag'),
                                ('filter', '@filter')],
                      formatters={'obs_time': 'datetime'})

    plot = figure(plot_width=600, plot_height=300,#title='Photometry',
                  tools='box_zoom,pan,reset', active_drag='box_zoom',
                  y_range=(max(observed.data['mag']) + 0.1,
                           min(observed.data['mag']) - 0.1))
    plot.add_tools(hover)
    plot.scatter(x='obs_time', y='mag', color='color', source=observed)
    plot.add_layout(Whisker(source=observed, base='obs_time', upper='max', lower='min'))
    plot.scatter(x='obs_time', y='lim_mag', color='color',
                 marker='inverted_triangle', source=unobserved)
    plot.xaxis.axis_label = 'Observation Date'
    plot.xaxis.formatter = DatetimeTickFormatter(hours=['%D'], days=['%D'],
                                                 months=['%D'], years=['%D'])

    return _plot_to_json(plot)


def spectroscopy_plot(source_id):
    spectra = Source.query.get(source_id).spectra
    hover = HoverTool(tooltips=[('wavelength', '$x'), ('flux', '$y')])
    plot = figure(plot_width=600, plot_height=300,#title='Spectroscopy',
               tools='box_zoom,pan,reset', active_drag='box_zoom')
    plot.add_tools(hover)
    # TODO y-axis units...?
    for s in spectra:
        plot.line(x=s.wavelengths, y=s.fluxes)
    plot.xaxis.axis_label = 'Wavelength (Å)'
    plot.yaxis.axis_label = 'Flux'

    return _plot_to_json(plot)
