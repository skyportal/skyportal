from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from .... import plot


# TODO this should distinguish between "no data to plot" and "plot failed"
class PlotPhotometryHandler(BaseHandler):
    @auth_or_token
    def get(self, source_id):
        docs_json, render_items, custom_model_js = plot.photometry_plot(source_id)
        if docs_json is None:
            self.success(data={'docs_json': None, 'url': self.request.path})
        else:
            self.success(data={'docs_json': docs_json, 'render_items': render_items,
                               'custom_model_js': custom_model_js,
                               'url': self.request.path})


class PlotSpectroscopyHandler(BaseHandler):
    @auth_or_token
    def get(self, source_id):
        docs_json, render_items, custom_model_js = plot.spectroscopy_plot(source_id)
        if docs_json is None:
            self.success(data={'docs_json': None, 'url': self.request.path})
        else:
            self.success(data={'docs_json': docs_json, 'render_items': render_items,
                               'custom_model_js': custom_model_js,
                               'url': self.request.path})
