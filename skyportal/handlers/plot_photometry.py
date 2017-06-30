from baselayer.app.handlers.base import BaseHandler
from .. import plot

import tornado.web


class PlotPhotometryHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, source_id):
        docs_json, render_items = plot.photometry_plot(source_id)
        if docs_json is None:
            self.error(f"Could not generate plot for source {source_id}")
        else:
            self.success({'docs_json': docs_json, 'render_items': render_items})
