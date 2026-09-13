import ast
import base64
import functools
import glob
import io
import json
import os
import subprocess
import tempfile
import traceback
import uuid
import zipfile

import joblib
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import tornado.escape
import tornado.web
from astropy.table import Table
from tornado.ioloop import IOLoop

from baselayer.app.env import load_env
from baselayer.log import make_log

_, cfg = load_env()
log = make_log("ngsf_analysis_service")

# we need to set the backend here to insure we
# can render the plot headlessly
matplotlib.use("Agg")
rng = np.random.default_rng()

default_analysis_parameters = {"fix_z": False}


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


def run_ngsf_model(data_dict):
    """
    Use Next Generation SuperFit (`ngsf`) to fit data to a model with name `source_name`.

    For this analysis, we expect the `inputs` dictionary to have the following keys:
       - source: the name of the model to fit to the data
       - fix_z: whether to fix the redshift
       - photometry: the photometry to fit to the model (in csv format)
       - redshift: the known redshift of the object

    Other analysis services may require additional keys in the `inputs` dictionary.
    """
    analysis_parameters = data_dict["inputs"].get("analysis_parameters", {})
    analysis_parameters = {**default_analysis_parameters, **analysis_parameters}

    fix_z = analysis_parameters.get("fix_z") in [True, "True", "t", "true"]

    # this example analysis service expects the spectroscopy to be in
    # a csv file (at data_dict["inputs"]["spectroscopy"]) with the following columns
    # - wavelengths: wavelengths of the spectrum
    # - fluxes: fluxes of the spectrum
    #
    # the following code transforms these inputs from SkyPortal
    # to the format expected by Next Generation SuperFit.
    #

    rez = {"status": "failure", "message": "", "analysis": {}}
    try:
        data = pd.read_csv(io.StringIO(data_dict["inputs"]["spectra"]))

        redshift = Table.read(data_dict["inputs"]["redshift"], format="ascii.csv")
        z = redshift["redshift"][0]
    except Exception as e:
        rez.update(
            {
                "status": "failure",
                "message": f"input data is not in the expected format {e}",
            }
        )
        return rez

    if fix_z and np.ma.is_masked(z):
        rez.update(
            {
                "status": "failure",
                "message": "Need redshift if fixing redshift",
            }
        )
        return rez

    # we will need to write to temp files
    # locally and then write their contents
    # to the results dictionary for uploading
    local_temp_files = []

    SUPERFIT_PATH = "services/ngsf_analysis_service/NGSF"
    SUPERFIT_DATA_PATH = f"{SUPERFIT_PATH}/data"
    # Maintained NGSF fork, pinned to a commit so the fit is reproducible and does
    # not break on upstream drift. SUPERFIT_PATH is the repo root and
    # SUPERFIT_PATH/NGSF the importable package; the template bank downloads
    # alongside it.
    NGSF = "https://github.com/skyportal/NGSF.git"
    NGSF_COMMIT = "f1129ac"
    # Bank mirror hosted on the fork's releases: WISeREP rate-limits and 403s
    # repeated automated pulls, which breaks a fresh clone's first fit.
    NGSF_bank = "https://github.com/skyportal/NGSF/releases/download/template-bank-v1/supyfit_bank.zip"
    NGSF_zip = f"{SUPERFIT_PATH}/{NGSF_bank.split('/')[-1]}"

    if not os.path.isdir(SUPERFIT_PATH):
        os.makedirs(SUPERFIT_PATH)
        os.system(f"git clone {NGSF} {SUPERFIT_PATH}")
        os.system(f"cd {SUPERFIT_PATH}; git checkout {NGSF_COMMIT}")
        curl_command = f'curl -L -H "Content-Type: application/json" -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36" -o {NGSF_zip} {NGSF_bank}'
        os.system(curl_command)
        with zipfile.ZipFile(NGSF_zip, "r") as zp:
            zp.extractall(SUPERFIT_PATH)

    os.makedirs(SUPERFIT_DATA_PATH, exist_ok=True)
    for sub in ("fit_results", "fit_results_z"):
        os.makedirs(os.path.join(SUPERFIT_PATH, sub), exist_ok=True)

    # The bank zip may unpack binnings/ at its root or one level down; find it.
    bank_hits = glob.glob(f"{SUPERFIT_PATH}/**/binnings", recursive=True)
    bank_dir = os.path.dirname(bank_hits[0]) if bank_hits else SUPERFIT_PATH

    # run.py reads its base config from NGSFCONFIG and takes the spectrum, the
    # redshift and the wavelength window positionally. Start from the fork's
    # shipped template and point pkg_dir/bank_dir at this checkout.
    NGSF_CONFIG = os.path.abspath(
        os.path.join(SUPERFIT_PATH, "config", "job_parameters.json")
    )
    base_cfg = json.loads(
        open(os.path.join(SUPERFIT_PATH, "config", "parameters.json")).read()
    )
    base_cfg["pkg_dir"] = os.path.abspath(SUPERFIT_PATH) + "/"
    base_cfg["bank_dir"] = os.path.abspath(bank_dir) + "/"
    base_cfg["show_plot"] = 0
    base_cfg["show_plot_png"] = 1
    with open(NGSF_CONFIG, "w") as fcfg:
        json.dump(base_cfg, fcfg)
    WAV_MIN, WAV_MAX = 4000.0, 9500.0

    local_temp_files = []
    plot_data = []

    try:
        for index, row in data.iterrows():
            filebase = str(uuid.uuid4())
            SPECFILE = f"{SUPERFIT_DATA_PATH}/{filebase}.dat"
            wavelengths = np.array(ast.literal_eval(row["wavelengths"]))

            # we might have some issues reading `nan` values, so we need to
            # convert them to `None` first
            fluxes = row["fluxes"].replace("nan", "None")
            fluxes = np.array(ast.literal_eval(fluxes))
            # then we convert `None` values back to `np.nan`
            fluxes = np.array([np.nan if x is None else x for x in fluxes])

            with open(SPECFILE, "w") as fid:
                for w, f in zip(wavelengths.tolist(), fluxes.tolist()):
                    fid.write(f"{w} {f}\n")

            # z=100 runs the free-redshift scan (results in fit_results/); any
            # other value pins that redshift (results in fit_results_z/).
            z_arg = float(z) if fix_z else 100.0
            env = {
                **os.environ,
                "NGSFCONFIG": NGSF_CONFIG,
                "PYTHONPATH": os.path.abspath(SUPERFIT_PATH),
                "MPLBACKEND": "Agg",
            }
            subprocess.call(
                [
                    "python",
                    "run.py",
                    f"data/{filebase}.dat",
                    str(z_arg),
                    str(WAV_MIN),
                    str(WAV_MAX),
                ],
                cwd=SUPERFIT_PATH,
                env=env,
            )
            results_subdir = "fit_results_z" if fix_z else "fit_results"

            results_path = os.path.join(
                SUPERFIT_PATH, results_subdir, f"{filebase}.csv"
            )
            results = pd.read_csv(results_path)
            results.sort_values(by=["CHI2/dof"], inplace=True)

            plot_file = os.path.join(SUPERFIT_DATA_PATH, f"{filebase}.png")
            plt.figure(figsize=(20, 10))
            ax = plt.gca()
            y_pos = np.arange(len(results["SN"]))
            ax.barh(y_pos, results["CHI2/dof"], align="center")
            ax.set_yticks(y_pos, labels=results["SN"])
            ax.set_xlabel("CHI2/dof")
            ax.set_xscale("log")
            ax.set_xlim(
                [np.min(results["CHI2/dof"]) - 0.5, np.max(results["CHI2/dof"]) + 0.5]
            )
            plt.savefig(plot_file, bbox_inches="tight")
            plt.close()

            f = tempfile.NamedTemporaryFile(
                suffix=".png", prefix="ngsfplot_", delete=False
            )
            f.close()
            plot_data_1 = base64.b64encode(open(plot_file, "rb").read())
            local_temp_files.append(f.name)

            f = tempfile.NamedTemporaryFile(
                suffix=".png", prefix="ngsfplot_", delete=False
            )
            f.close()
            plot_file = os.path.join(
                SUPERFIT_PATH, results_subdir, f"{filebase}_ngsf0.png"
            )
            plot_data_2 = base64.b64encode(open(plot_file, "rb").read())
            local_temp_files.append(f.name)

            plot_data.append({"format": "png", "data": plot_data_1})
            plot_data.append({"format": "png", "data": plot_data_2})

            f = tempfile.NamedTemporaryFile(
                suffix=".joblib", prefix="results_", delete=False
            )
            f.close()
            joblib.dump(results.to_json(orient="index"), f.name, compress=3)
            result_data = base64.b64encode(open(f.name, "rb").read())
            local_temp_files.append(f.name)

        analysis_results = {
            "plots": plot_data,
            "results": {"format": "joblib", "data": result_data},
        }
        rez.update(
            {
                "analysis": analysis_results,
                "status": "success",
                "message": f"Good results with chi^2/dof={np.min(results['CHI2/dof'])}",
            }
        )

    except Exception as e:
        log(f"Exception while running the model: {e}")
        log(f"{traceback.format_exc()}")
        log(f"Data: {data}")
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

        def ngsf_analysis_done_callback(
            future,
            logger=log,
            data_dict=data_dict,
        ):
            """
            Callback function for when the ngsf analysis service is done.
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

        runner = functools.partial(run_ngsf_model, data_dict)
        future_result = IOLoop.current().run_in_executor(None, runner)
        future_result.add_done_callback(ngsf_analysis_done_callback)

        return self.write(
            {"status": "pending", "message": "ngsf_analysis_service: analysis started"}
        )


def make_app():
    return tornado.web.Application(
        [
            (r"/analysis/ngsf_analysis", MainHandler),
        ]
    )


if __name__ == "__main__":
    ngsf_analysis = make_app()
    port = cfg["analysis_services.ngsf_analysis_service.port"]
    ngsf_analysis.listen(port)
    log(f"Listening on port {port}")
    tornado.ioloop.IOLoop.current().start()
