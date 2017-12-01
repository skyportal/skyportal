from baselayer.app.handlers.base import BaseHandler
from .. import plot

import tornado.web


# TODO this should distinguish between "no data to plot" and "plot failed"
class PlotPhotometryHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, source_id):
        docs_json, render_items, custom_model_js = plot.photometry_plot(source_id)
        if docs_json is None:
            self.error(f"Could not generate plot for source {source_id}")
        else:
            self.success({'docs_json': docs_json, 'render_items': render_items,
                          'custom_model_js': custom_model_js,
                          'url': self.request.path})


class PlotSpectroscopyHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, source_id):
        docs_json, render_items, custom_model_js = plot.spectroscopy_plot(source_id)
        if docs_json is None:
            self.error(f"Could not generate plot for source {source_id}")
        else:
            self.success({'docs_json': docs_json, 'render_items': render_items,
                          'custom_model_js': custom_model_js,
                          'url': self.request.path})
