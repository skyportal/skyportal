import base64
import functools
import io
import json
import os
import tempfile
import traceback

import joblib
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pysedm
import requests
import tornado.escape
import tornado.web
from tornado.ioloop import IOLoop

from baselayer.app.env import load_env
from baselayer.log import make_log

_, cfg = load_env()
log = make_log("spectral_cube_analysis_service")

matplotlib.use("Agg")
rng = np.random.default_rng()

default_analysis_parameters = {
    "centroid_x": None,
    "centroid_y": None,
    "spaxel_buffer": None,
    "fluxcal_data": None,
}


def upload_analysis_results(results, data_dict, request_timeout=60):
    """
    Upload the results to the webhook.
    """

    log("Uploading results to webhook")
    if data_dict["callback_method"] != "POST":
        log("Callback URL is not a POST URL. Skipping.")
        return
    url = data_dict["callback_url"]
    try:
        _ = requests.post(
            url,
            json=results,
            timeout=request_timeout,
        )
    except requests.exceptions.Timeout:
        # If we timeout here then it's precisely because
        # we cannot write back to the SkyPortal instance.
        # So returning something doesn't make sense in this case.
        # Just log it and move on...
        log("Callback URL timedout. Skipping.")
    except Exception as e:
        log(f"Callback exception {e}.")


def run_spectral_cube_model(data_dict):
    """
    Run the spectral cube analysis model using pysedm.

    For this analysis, we expect the data_dict to contain:
    - `image_data`: base64 encoded image data
    and optionally:
    - `centroid_x`: x centroid of the object
    - `centroid_y`: y centroid of the object
    - `spaxel_buffer`: buffer around the centroid to use for the analysis
    - `fluxcal_data`: base64 encoded image data for the flux calibration
    """
    analysis_parameters = data_dict["inputs"].get("analysis_parameters", {})
    analysis_parameters = {**default_analysis_parameters, **analysis_parameters}

    # decode the image data
    file_data = analysis_parameters["image_data"]
    centroid_x = analysis_parameters["centroid_x"]
    centroid_y = analysis_parameters["centroid_y"]
    spaxel_buffer = analysis_parameters["spaxel_buffer"]

    rez = {"status": "failure", "message": "", "analysis": {}}
    if file_data is None:
        rez["message"] = "No image data provided"
        return rez
    # if centroid_x, centroid_y, and spaxel_buffer are not None and not numbers, then return error
    if (
        (centroid_x is not None)
        and (centroid_y is not None)
        and (spaxel_buffer is not None)
    ):
        try:
            centroid_x = float(centroid_x)
            centroid_y = float(centroid_y)
            spaxel_buffer = float(spaxel_buffer)
        except ValueError:
            rez["message"] = "Centroid x/y and spaxel buffer must be numbers or None"
            return rez

    local_temp_files = []
    try:
        file_data = file_data.split("base64,")
        file_name = file_data[0].split("name=")[1].split(";")[0]

        if file_name.endswith(".fz"):
            suffix = ".fits.fz"
        else:
            suffix = ".fits"
        prefix = file_name.split(".")[0]

        with tempfile.NamedTemporaryFile(
            prefix=prefix, suffix=suffix, mode="wb", delete=True
        ) as f:
            file_data = base64.b64decode(file_data[-1])
            f.write(file_data)
            f.flush()

            cube = pysedm.get_sedmcube(f.name)

            centroid_data = {}
            if (centroid_x is not None) and (centroid_y is not None):
                centroid_data["centroid"] = (centroid_x, centroid_y)
            else:
                centroid_data["centroid"] = "max"

            if spaxel_buffer is not None:
                centroid_data["spaxelbuffer"] = spaxel_buffer
            cube.extract_pointsource(**centroid_data)

            fluxcal_data = analysis_parameters["fluxcal_data"]
            if fluxcal_data is not None:
                file_data = fluxcal_data.split("base64,")
                file_name = file_data[0].split("name=")[1].split(";")[0]
                # if image name contains (.fz) then it is a compressed file
                if file_name.endswith(".fz"):
                    suffix = ".fits.fz"
                else:
                    suffix = ".fits"
                prefix = file_name.split(".")[0]

                with tempfile.NamedTemporaryFile(
                    prefix=prefix, suffix=suffix, mode="wb", delete=True
                ) as g:
                    file_data = base64.b64decode(file_data[-1])
                    g.write(file_data)
                    g.flush()

                    spectrum = cube.extractstar.get_fluxcalibrated_spectrum(
                        fluxcalfile=g.name
                    )
            else:
                spectrum = cube.extractstar.get_fluxcalibrated_spectrum(nofluxcal=True)

            #  TODO: use the spectrum and an instrument_id to post spectra back to SkyPortal

            result = {
                "lbda": spectrum.data.tolist(),
                "data": spectrum.lbda.tolist(),
            }

            f = tempfile.NamedTemporaryFile(
                suffix=".joblib", prefix="results_", delete=False
            )
            f.close()
            joblib.dump(result, f.name, compress=3)
            result_data = base64.b64encode(open(f.name, "rb").read())
            local_temp_files.append(f.name)

            figsize = (16, 6)
            fig = plt.figure(figsize=figsize, constrained_layout=False)
            ax1 = fig.add_subplot(1, 3, (1, 2))
            ax2 = fig.add_subplot(1, 3, 3)

            # SPECTRUM PLOT
            spectrum.show(ax=ax1)
            ax1.set_title("Spectrum plot: Flux (AU) vs Wavelength (Å)")
            ax1.set_xlabel("Wavelength (Å)")
            ax1.set_ylabel("Flux (AU)")

            # CUBE PLOT
            cube.extractstar.show_mla(ax=ax2)
            ax2.set_title("Cube plot: RA vs Dec (spaxels)")
            ax2.set_xlabel("RA (spaxels)")
            ax2.set_ylabel("Dec (spaxels)")

            fig.suptitle("Spectrum at the centroid", fontsize=16)

            buf = io.BytesIO()
            fig.savefig(buf, format="png")
            plt.close(fig)
            buf.seek(0)

            plot_data = base64.b64encode(buf.read())

            analysis_results = {
                "plots": [
                    {"format": "png", "data": plot_data},
                ],
                "results": {"format": "joblib", "data": result_data},
            }
            rez.update(
                {
                    "analysis": analysis_results,
                    "status": "success",
                    "message": "Good results",
                }
            )
    except Exception as e:
        log(f"Exception: {e}")
        rez.update({"status": "failure", "message": f"problem running the model {e}"})
    finally:
        # clean up local files
        for f in local_temp_files:
            try:
                os.remove(f)
            except:  # noqa E722
                pass

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
        """
        Analysis endpoint which sends the `data_dict` off for
        processing, returning immediately. The idea here is that
        the analysis model may take awhile to run so we
        need async behavior.
        """
        try:
            data_dict = tornado.escape.json_decode(self.request.body)
        except json.decoder.JSONDecodeError:
            err = traceback.format_exc()
            log(f"JSON decode error: {err}")
            return self.error(400, "Invalid JSON")

        required_keys = ["inputs", "callback_url", "callback_method"]
        for key in required_keys:
            if key not in data_dict:
                log(f"missing required key {key} in data_dict")
                return self.error(400, f"missing required key {key} in data_dict")

        def spectral_cube_analysis_done_callback(
            future,
            logger=log,
            data_dict=data_dict,
        ):
            """
            Callback function for when the spectral cube analysis service is done.
            Sends back results/errors via the callback_url.

            This is run synchronously after the future completes
            so there is no need to await for `future`.
            """
            try:
                result = future.result()
            except Exception as e:
                # catch all the exceptions and log them,
                # try to write back to SkyPortal something
                # informative.
                logger(f"{str(future.exception())[:1024]} {e}")
                result = {
                    "status": "failure",
                    "message": f"{str(future.exception())[:1024]}{e}",
                }
            finally:
                upload_analysis_results(result, data_dict)

        runner = functools.partial(run_spectral_cube_model, data_dict)
        future_result = IOLoop.current().run_in_executor(None, runner)
        future_result.add_done_callback(spectral_cube_analysis_done_callback)

        return self.write(
            {
                "status": "pending",
                "message": "spectral_cube_analysis_service: analysis started",
            }
        )


def make_app():
    return tornado.web.Application(
        [
            (r"/analysis/spectral_cube_analysis", MainHandler),
        ]
    )


if __name__ == "__main__":
    spectral_cube_analysis = make_app()
    port = cfg["analysis_services.spectral_cube_analysis_service.port"]
    spectral_cube_analysis.listen(port)
    log(f"Listening on port {port}")
    tornado.ioloop.IOLoop.current().start()
