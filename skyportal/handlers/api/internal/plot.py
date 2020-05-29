from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from .... import plot


# TODO this should distinguish between "no data to plot" and "plot failed"
class PlotPhotometryHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        height = self.get_query_argument("plotHeight", 300)
        width = self.get_query_argument("plotWidth", 600)
        docs_json, render_items, custom_model_js = plot.photometry_plot(
            obj_id, height=int(height), width=int(width),
        )
        if docs_json is None:
            self.success(data={'docs_json': None, 'url': self.request.path})
        else:
            self.success(data={'docs_json': docs_json, 'render_items': render_items,
                               'custom_model_js': custom_model_js,
                               'url': self.request.uri})


class PlotSpectroscopyHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        docs_json, render_items, custom_model_js = plot.spectroscopy_plot(obj_id)
        if docs_json is None:
            self.success(data={'docs_json': None, 'url': self.request.path})
        else:
            self.success(data={'docs_json': docs_json, 'render_items': render_items,
                               'custom_model_js': custom_model_js,
                               'url': self.request.path})
