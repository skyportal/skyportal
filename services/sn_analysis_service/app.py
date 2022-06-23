import os
import functools
import tempfile
import io

import numpy as np
import matplotlib
import arviz as az
from quart import Quart
from quart import request
from astropy.table import Table
import sncosmo

from baselayer.log import make_log
from baselayer.app.env import load_env

_, cfg = load_env()
log = make_log('sn_analysis_service')

# we need to set the backend here to insure we
# can render the plot headlessly
matplotlib.use('Agg')
rng = np.random.default_rng()

app = Quart(__name__)
app.debug = False

default_analysis_parameters = {"source": "nugent-sn2p", "fix_z": False}


def upload_analysis_results(results, data_dict):
    """
    Upload the results to the webhook.

    TO BE COMPLETED
    """
    log("upload results to webhook")
    assert isinstance(results, dict)
    assert isinstance(data_dict, dict)
    pass


async def run_sn_model(dd):
    """
    Use `sncosmo` to fit data to a model with name `source_name`.

    We expect the `inputs` dictionary to have the following keys:
       - source: the name of the model to fit to the data
       - fix_z: whether to fix the redshift
       - photometry: the photometry to fit to the model (in csv format)
       - redshift: the known redshift of the object

    TODO in the next PR: send the results back to the webhook

    """
    data_dict = await dd

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
    # to the format expected by sncosmo.
    #
    results = {"status": "success", "message": "", "data": {}}
    try:
        data = Table.read(data_dict["inputs"]["photometry"], format='ascii.csv')
        data.rename_column('mjd', 'time')
        data.rename_column('filter', 'band')
        data.rename_column('magsys', 'zpsys')

        data['flux'].fill_value = 1e-6
        data = data.filled()
        data.sort("time")

        redshift = Table.read(data_dict["inputs"]["redshift"], format='ascii.csv')
        z = redshift['redshift'][0]
    except Exception as e:
        results.update(
            {
                "status": "failure",
                "message": f"input data is not in the expected format {e}",
            }
        )
        upload_analysis_results(results, data_dict)

    try:
        model = sncosmo.Model(source=source)

        if fix_z:
            if z is not None:
                model.set(z=z)
                bounds = {'z': (z, z)}
            else:
                raise ValueError("No redshift provided but `fix_z` requested.")
        else:
            bounds = {'z': (0.01, 1.0)}

        # run the fit
        result, fitted_model = sncosmo.fit_lc(
            data,
            model,
            model.param_names,
            bounds=bounds,
        )
        log(f"Number of χ² function calls: {result.ncall}")
        log(f"Number of degrees of freedom in fit: {result.ndof}")
        log(f"χ² value at minimum: {result.chisq}")
        log(f"model parameters: {result.param_names}")
        log(f"best-fit values: {result.parameters}")
        log(f"The result contains the following attributes:\n {result.keys()}")
        log(f'{result["success"]=}')

        if result["success"]:

            with tempfile.NamedTemporaryFile(
                suffix=".png", prefix="snplot_", dir="/tmp/"
            ) as f:
                _ = sncosmo.plot_lc(
                    data,
                    model=fitted_model,
                    errors=result.errors,
                    model_label=source,
                    zp=23.9,
                    figtext=data_dict["resource_id"],
                    fname=f.name,
                )
                f.seek(0)
                plot_data = io.BytesIO(f.read())
                f.close()
                os.remove(f.name)
                log('made lightcurve plot')

            # make some draws from the posterior (simulating what we'd expect
            # with an MCMC analysis)
            post = rng.multivariate_normal(result.parameters, result.covariance, 10000)
            post = post[np.newaxis, :]
            # create an inference dataset
            dataset = az.convert_to_inference_data(
                {x: post[:, :, i] for i, x in enumerate(result.param_names)}
            )
            results.update({"data": {"posterior": dataset, "plot": plot_data}})
        else:
            results.update({"status": "failure", "message": "model failed to converge"})

    except Exception as e:
        results.update(
            {"status": "failure", "message": f"problem running the model {e}"}
        )

    # TODO in the next PR #3:
    # return the dataset and the plot data
    # by calling the webhook
    upload_analysis_results(results, data_dict)


@app.route('/analysis/demo_analysis', methods=['POST'])
async def demo_analysis():
    """
    Analysis endpoint which sends the `data_dict` off for
    processing, returning immediately. The idea here is that
    the analysis model may take awhile to run so we
    need async behavior.
    """
    log(f'{request.method} {request.url}')
    data_dict = request.get_json(silent=True)

    runner = functools.partial(run_sn_model, data_dict)

    app.add_background_task(runner)

    return "sn_analysis_service: analysis started"


if __name__ == "__main__":
    app.run(port=cfg['analysis_services.sn_analysis_service.port'])
