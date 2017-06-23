from baselayer.app.handlers.base import BaseHandler
from .. import plot

import tornado.web


class PlotPhotometryHandler(BaseHandler):
    def get(self, source_id):
        docs_json, render_items = plot.photometry_plot(source_id)
        self.success({'docs_json': docs_json, 'render_items': render_items})
