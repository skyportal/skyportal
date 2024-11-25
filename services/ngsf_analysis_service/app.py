import ast
from astropy.table import Table
import joblib
import io
import os
import functools
import tempfile
import base64
import traceback
import json
import subprocess
import uuid
import zipfile

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import requests

from tornado.ioloop import IOLoop
import tornado.web
import tornado.escape

from baselayer.log import make_log
from baselayer.app.env import load_env

_, cfg = load_env()
log = make_log('ngsf_analysis_service')

# we need to set the backend here to insure we
# can render the plot headlessly
matplotlib.use('Agg')
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

        redshift = Table.read(data_dict["inputs"]["redshift"], format='ascii.csv')
        z = redshift['redshift'][0]
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

    SUPERFIT_PATH = 'services/ngsf_analysis_service/NGSF'
    SUPERFIT_DATA_PATH = f'{SUPERFIT_PATH}/data'
    SUPERFIT_PARAMETERS_JSON = 'services/ngsf_analysis_service/parameters.json'
    NGSF = "https://github.com/samanthagoldwasser25/NGSF.git"
    NGSF_bank = "https://www.wiserep.org/sites/default/files/supyfit_bank.zip"
    NGSF_zip = f"{SUPERFIT_PATH}/{NGSF_bank.split('/')[-1]}"

    if not os.path.isdir(SUPERFIT_PATH):
        os.makedirs(SUPERFIT_PATH)
        git_command = f"git clone {NGSF} {SUPERFIT_PATH}"
        os.system(git_command)
        curl_command = f'curl -L -H "Content-Type: application/json" -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36" -o {NGSF_zip} {NGSF_bank}'
        os.system(curl_command)

        with zipfile.ZipFile(NGSF_zip, "r") as zp:
            zp.extractall(SUPERFIT_PATH)

        # NGSF is somewhat outdated, and uses np.float which doesn't exist anymore in a method called
        # JD, in get_metadata.py. We need to change it to float. For that we simply
        # open the file and replace the string.
        with open(f"{SUPERFIT_PATH}/NGSF/get_metadata.py") as file:
            filedata = file.read()

        # Replace the target string
        filedata = filedata.replace("np.float", "float")

        # Write the file out again
        with open(f"{SUPERFIT_PATH}/NGSF/get_metadata.py", "w") as file:
            file.write(filedata)

    if not os.path.isdir(SUPERFIT_DATA_PATH):
        os.makedirs(SUPERFIT_DATA_PATH)

    local_temp_files = []
    plot_data = []

    try:
        for index, row in data.iterrows():
            filebase = str(uuid.uuid4())
            SPECFILE = f'{SUPERFIT_DATA_PATH}/{filebase}.dat'
            wavelengths = np.array(ast.literal_eval(row['wavelengths']))
            fluxes = np.array(ast.literal_eval(row['fluxes']))
            with open(SPECFILE, 'w') as fid:
                for w, f in zip(wavelengths.tolist(), fluxes.tolist()):
                    fid.write(f'{w} {f}\n')

            params = json.loads(open(SUPERFIT_PARAMETERS_JSON).read())
            params['object_to_fit'] = f'data/{filebase}.dat'
            if fix_z:
                params['use_exact_z'] = 1
                params['z_exact'] = z

            JSON_FILE = f'{SUPERFIT_DATA_PATH}/{filebase}.json'
            with open(JSON_FILE, 'w') as f:
                json.dump(params, f)

            subprocess.call(
                f'cd {SUPERFIT_PATH}; python run.py data/{filebase}.json', shell=True
            )

            results_path = os.path.join(SUPERFIT_PATH, f"{filebase}.csv")
            results = pd.read_csv(results_path)
            results.sort_values(by=['CHI2/dof'], inplace=True)

            plot_file = os.path.join(SUPERFIT_DATA_PATH, f'{filebase}.png')
            plt.figure(figsize=(20, 10))
            ax = plt.gca()
            y_pos = np.arange(len(results['SN']))
            ax.barh(y_pos, results['CHI2/dof'], align='center')
            ax.set_yticks(y_pos, labels=results['SN'])
            ax.set_xlabel('CHI2/dof')
            ax.set_xscale('log')
            ax.set_xlim(
                [np.min(results['CHI2/dof']) - 0.5, np.max(results['CHI2/dof']) + 0.5]
            )
            plt.savefig(plot_file, bbox_inches='tight')
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
            plot_file = os.path.join(SUPERFIT_PATH, f"{filebase}_0.png")
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
        self.set_header('Content-Type', 'application/json')

    def error(self, code, message):
        self.set_status(code)
        self.write({'message': message})

    def get(self):
        self.write({'status': 'active'})

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
            {'status': 'pending', 'message': 'ngsf_analysis_service: analysis started'}
        )


def make_app():
    return tornado.web.Application(
        [
            (r"/analysis/ngsf_analysis", MainHandler),
        ]
    )


if __name__ == "__main__":
    ngsf_analysis = make_app()
    port = cfg['analysis_services.ngsf_analysis_service.port']
    ngsf_analysis.listen(port)
    log(f'Listening on port {port}')
    tornado.ioloop.IOLoop.current().start()
