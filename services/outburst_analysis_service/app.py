import functools
import json
import traceback

import numpy as np
import requests
import tornado.escape
import tornado.web
from astropy.table import Table
from tornado.ioloop import IOLoop

from baselayer.app.env import load_env
from baselayer.log import make_log
from skyportal.utils.outburst import outburst_report

_, cfg = load_env()
log = make_log("outburst_analysis_service")

default_analysis_parameters = {"window": 14, "rh_slope": -2, "delta_slope": -2}


def upload_analysis_results(results, data_dict, request_timeout=60):
    """Upload the results to the webhook."""
    log("Uploading results to webhook")
    if data_dict["callback_method"] != "POST":
        log("Callback URL is not a POST URL. Skipping.")
        return
    try:
        requests.post(data_dict["callback_url"], json=results, timeout=request_timeout)
    except requests.exceptions.Timeout:
        log("Callback URL timedout. Skipping.")
    except Exception as e:
        log(f"Callback exception {e}.")


def serialize_report(report):
    """Make the outburst report JSON-safe (numpy arrays -> lists). The frontend
    renders the panels interactively from this, so no server-side plot."""
    out = {}
    for key, value in report.items():
        if isinstance(value, np.ndarray):
            out[key] = value.tolist()
        elif isinstance(value, dict):
            out[key] = {k: float(v) for k, v in value.items()}
        else:
            out[key] = value
    return out


def run_outburst_analysis(data_dict):
    """Compute the outburst statistic for the trailing window of an SSO's
    photometry and return the full report as JSON for interactive display.

    Expects ``inputs.photometry`` (SkyPortal CSV) with ``mjd``, ``mag``,
    ``magerr``, ``filter``. Geometry (``rh``, ``delta``, ``phase``) is read from
    like-named columns (as BOOM will supply); the most recent point is tested.
    """
    params = {
        **default_analysis_parameters,
        **data_dict["inputs"].get("analysis_parameters", {}),
    }
    rez = {"status": "failure", "message": "", "analysis": {}}
    try:
        data = Table.read(data_dict["inputs"]["photometry"], format="ascii.csv")
        data = data[np.isfinite(np.array(data["mag"], dtype=float))]  # detections
        for col in ("rh", "delta", "phase"):
            if col not in data.colnames:
                raise ValueError(
                    f"photometry is missing geometry column '{col}' "
                    "(rh/delta/phase must be supplied)"
                )
    except Exception as e:
        rez["message"] = f"input data is not in the expected format: {e}"
        return rez

    try:
        report = outburst_report(
            np.array(data["mjd"], dtype=float),
            np.array(data["mag"], dtype=float),
            np.array(data["magerr"], dtype=float),
            np.array(data["filter"]),
            np.array(data["rh"], dtype=float),
            np.array(data["delta"], dtype=float),
            np.array(data["phase"], dtype=float),
            window=float(params["window"]),
            rh_slope=float(params["rh_slope"]),
            delta_slope=float(params["delta_slope"]),
        )
    except Exception as e:
        rez["message"] = f"could not compute the outburst statistic: {e}"
        return rez

    results = serialize_report(report)
    results["window_days"] = float(params["window"])
    rez.update(
        {
            "analysis": {"results": {"format": "json", "data": results}},
            "status": "success",
            "message": (
                f"median outburst statistic O={report['median_o']:.2f} "
                f"from {report['n_points']} points"
            ),
        }
    )
    return rez


class MainHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

    def error(self, code, message):
        self.set_status(code)
        self.write({"message": message})

    def get(self):
        self.write({"status": "active"})

    def post(self):
        try:
            data_dict = tornado.escape.json_decode(self.request.body)
        except json.decoder.JSONDecodeError:
            log(f"JSON decode error: {traceback.format_exc()}")
            return self.error(400, "Invalid JSON")

        for key in ("inputs", "callback_url", "callback_method"):
            if key not in data_dict:
                return self.error(400, f"missing required key {key} in data_dict")

        def done_callback(future, logger=log, data_dict=data_dict):
            try:
                result = future.result()
            except Exception as e:
                logger(f"{str(future.exception())[:1024]} {e}")
                result = {
                    "status": "failure",
                    "message": f"{str(future.exception())[:1024]}{e}",
                }
            finally:
                upload_analysis_results(result, data_dict)

        runner = functools.partial(run_outburst_analysis, data_dict)
        future_result = IOLoop.current().run_in_executor(None, runner)
        future_result.add_done_callback(done_callback)
        return self.write(
            {
                "status": "pending",
                "message": "outburst_analysis_service: analysis started",
            }
        )


def make_app():
    return tornado.web.Application([(r"/analysis/outburst", MainHandler)])


if __name__ == "__main__":
    app = make_app()
    port = cfg["analysis_services.outburst_analysis_service.port"]
    app.listen(port)
    log(f"Listening on port {port}")
    tornado.ioloop.IOLoop.current().start()
