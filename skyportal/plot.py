import numpy as np
import pandas as pd

from bokeh.core.json_encoder import serialize_json
from bokeh.document import Document
from bokeh.models import Whisker, DatetimeTickFormatter, HoverTool
from bokeh.plotting import figure, show, ColumnDataSource
from bokeh.util.serialization import make_id

from skyportal.models import DBSession, Source, Photometry


def photometry_plot(source_id):
    """Create scatter plot of photometry for source.

    Parameters
    ----------
    source_id: int
        ID of source to be plotted.

    Returns
    -------
    (str, str)
        Returns (docs_json, render_items) json for the desired plot.
    """
    color_map = {'ipr': 'yellow', 'rpr': 'red', 'g': 'green'}

    # TODO how to properly filter out junk values?
    data = pd.read_sql(Photometry
                           .query
                           .filter(Photometry.source_id == source_id)
                           .filter(Photometry.mag > 0)
                           .filter(Photometry.mag < 90)
                           .statement, DBSession().bind)
    if data.empty:
        return None, None

    data['min'] = data.mag + data.e_mag
    data['max'] = data.mag - data.e_mag
    data['color'] = [color_map[f] for f in data['filter']]
    source = ColumnDataSource(data)
    hover = HoverTool(tooltips=[('obs_time', '@obs_time{%D}'), ('mag', '@mag'),
                                ('filter', '@filter')],
                      formatters={'obs_time': 'datetime'})

    plot = figure(plot_width=600, plot_height=300, title='Photometry',
                  tools='box_zoom,pan,reset', active_drag='box_zoom',
                  y_range=(max(data.mag) + 0.1, min(data.mag) - 0.1))
    plot.add_tools(hover)
    plot.scatter(x='obs_time', y='mag', color='color', source=source)
    plot.add_layout(Whisker(source=source, base='obs_time', upper='max', lower='min'))
    plot.xaxis.formatter = DatetimeTickFormatter(hours=['%D'], days=['%D'],
                                                 months=['%D'], years=['%D'])

    # Convert plot to json objects necessary for rendering with bokeh on the
    # frontend
    render_items = [{'docid': plot._id, 'elementid': make_id()}]

    doc = Document()
    doc.add_root(plot)
    docs_json_inner = doc.to_json()
    docs_json = {render_items[0]['docid']: docs_json_inner}

    docs_json = serialize_json(docs_json)
    render_items = serialize_json(render_items)

    return docs_json, render_items
