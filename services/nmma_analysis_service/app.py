import os
import functools
import tempfile
import base64
import traceback
import json

import joblib
import numpy as np
import matplotlib
import arviz as az
import requests

from tornado.ioloop import IOLoop
import tornado.web
import tornado.escape

from astropy.time import Time
from astropy.table import Table
import bilby
from nmma.em.analysis import get_parser, main

from baselayer.log import make_log
from baselayer.app.env import load_env

_, cfg = load_env()
log = make_log('nmma_analysis_service')

# we need to set the backend here to insure we
# can render the plot headlessly
matplotlib.use('Agg')
rng = np.random.default_rng()

default_analysis_parameters = {"source": "Me2017", "fix_z": False}


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
        # So returning something does't make sense in this case.
        # Just log it and move on...
        log("Callback URL timedout. Skipping.")
    except Exception as e:
        log(f"Callback exception {e}.")


def run_nmma_model(data_dict):
    """
    Use `nmma` to fit data to a model with name `source_name`.

    For this analysis, we expect the `inputs` dictionary to have the following keys:
       - source: the name of the model to fit to the data
       - fix_z: whether to fix the redshift
       - photometry: the photometry to fit to the model (in csv format)
       - redshift: the known redshift of the object

    Other analysis services may require additional keys in the `inputs` dictionary.
    """
    analysis_parameters = data_dict["inputs"].get("analysis_parameters", {})
    analysis_parameters = {**default_analysis_parameters, **analysis_parameters}

    source = analysis_parameters.get("source")
    fix_z = analysis_parameters.get("fix_z") in [True, "True", "t", "true"]

    # this example analysis service expects the photometry to be in
    # a csv file (at data_dict["inputs"]["photometry"]) with the following columns
    # - filter: the name of the bandpass
    # - mjd: the modified Julian date of the observation
    # - magsys: the mag system (e.g. ab) of the observations
    # - flux: the flux of the observation
    #
    # the following code transforms these inputs from SkyPortal
    # to the format expected by nmma.
    #
    rez = {"status": "failure", "message": "", "analysis": {}}
    try:
        data = Table.read(data_dict["inputs"]["photometry"], format='ascii.csv')
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

    # we will need to write to temp files
    # locally and then write their contents
    # to the results dictionary for uploading
    local_temp_files = []
    cand_name = data_dict['resource_id']

    prior_directory = f"{os.path.dirname(os.path.realpath(__file__))}/priors"
    svdmodel_directory = f"{os.path.dirname(os.path.realpath(__file__))}/svdmodels"

    try:
        ##########################
        # Setup parameters and fit
        ##########################
        plotdir = tempfile.mkdtemp()

        # cpus = 2
        nlive = 32
        error_budget = 1.0

        tmin = 0.01
        tmax = 7
        dt = 0.1
        Ebv_max = 0.5724

        t0 = np.min(data['mjd'])
        interpolation_type = "sklearn_gp"
        sampler = "dynesty"

        prior = f"{prior_directory}/{source}.prior"
        if not os.path.isfile(prior):
            log(f"Prior file for model {source} does not exist")
            return
        priors = bilby.gw.prior.PriorDict(prior)
        if fix_z:
            if z is not None:
                from astropy.cosmology import Planck18 as cosmo

                priors['luminosity_distance'] = cosmo.luminosity_distance(z).value
            else:
                raise ValueError("No redshift provided but `fix_z` requested.")
        priors.to_file(plotdir, source)
        prior = os.path.join(plotdir, f'{source}.prior')
        local_temp_files.append(prior)

        # output the data
        # in the format desired by NMMA
        f = tempfile.NamedTemporaryFile(suffix=".dat", mode="w", delete=False)
        for row in data:
            tt = Time(row['mjd'], format='mjd').isot
            filt = row['filter'][-1]
            mag = row['mag']
            magerr = row['magerr']
            f.write(f"{tt} {filt} {mag} {magerr}\n")
        f.close()
        local_temp_files.append(f.name)

        parser = get_parser()
        args = parser.parse_args(
            [
                '--model',
                source,
                '--svd-path',
                svdmodel_directory,
                '--outdir',
                plotdir,
                '--label',
                f'{cand_name}_{source}',
                '--trigger-time',
                str(t0),
                '--data',
                f.name,
                '--prior',
                prior,
                '--tmin',
                str(tmin),
                '--tmax',
                str(tmax),
                '--dt',
                str(dt),
                '--error-budget',
                str(error_budget),
                '--nlive',
                str(nlive),
                '--Ebv-max',
                str(Ebv_max),
                '--interpolation_type',
                interpolation_type,
                '--sampler',
                sampler,
                '--plot',
            ]
        )
        main(args=args)

        posterior_file = os.path.join(
            plotdir, f"{cand_name}_{source}_posterior_samples.dat"
        )
        json_file = os.path.join(plotdir, f"{cand_name}_{source}_result.json")

        if os.path.isfile(posterior_file):

            tab = Table.read(posterior_file, format='csv', delimiter=' ')
            inference = az.convert_to_inference_data(
                tab.to_pandas().to_dict(orient='list')
            )
            f = tempfile.NamedTemporaryFile(
                suffix=".nc", prefix="inferencedata_", delete=False
            )
            f.close()
            inference.to_netcdf(f.name)
            inference_data = base64.b64encode(open(f.name, 'rb').read())
            local_temp_files.append(f.name)

            with open(json_file) as f:
                result = json.load(f)

            f = tempfile.NamedTemporaryFile(
                suffix=".png", prefix="nmmaplot_", delete=False
            )
            f.close()
            plot_file = os.path.join(plotdir, "lightcurves.png")
            plot_data = base64.b64encode(open(plot_file, "rb").read())
            local_temp_files.append(f.name)

            f = tempfile.NamedTemporaryFile(
                suffix=".joblib", prefix="results_", delete=False
            )
            f.close()
            joblib.dump(result, f.name, compress=3)
            result_data = base64.b64encode(open(f.name, "rb").read())
            local_temp_files.append(f.name)

            analysis_results = {
                "inference_data": {"format": "netcdf4", "data": inference_data},
                "plots": [{"format": "png", "data": plot_data}],
                "results": {"format": "joblib", "data": result_data},
            }
            rez.update(
                {
                    "analysis": analysis_results,
                    "status": "success",
                    "message": f"Good results with log Bayes factor={result['log_bayes_factor']}",
                }
            )
        else:
            log("Fit failed.")
            rez.update({"status": "failure", "message": "model failed to converge"})

    except Exception as e:
        log(f"Exception while running the model: {e}")
        log(f"{traceback.format_exc()}")
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

        def nmma_analysis_done_callback(
            future,
            logger=log,
            data_dict=data_dict,
        ):
            """
            Callback function for when the nmma analysis service is done.
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

        runner = functools.partial(run_nmma_model, data_dict)
        future_result = IOLoop.current().run_in_executor(None, runner)
        future_result.add_done_callback(nmma_analysis_done_callback)

        return self.write(
            {'status': 'pending', 'message': 'nmma_analysis_service: analysis started'}
        )


def make_app():
    return tornado.web.Application(
        [
            (r"/analysis/nmma_analysis", MainHandler),
        ]
    )


if __name__ == "__main__":
    nmma_analysis = make_app()
    port = cfg['analysis_services.nmma_analysis_service.port']
    nmma_analysis.listen(port)
    log(f'NMMA Service Listening on port {port}')
    tornado.ioloop.IOLoop.current().start()
