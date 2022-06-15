import functools
import time

import matplotlib

from quart import Quart
from quart import request
from astropy.table import Table
import sncosmo
from baselayer.log import make_log
from baselayer.app.env import load_env

_, cfg = load_env()
log = make_log('sn_analysis_service')

matplotlib.use('Agg')

app = Quart(__name__)
app.debug = False

default_source_name = "nugent-sn2p"
default_fix_z = False


async def run_sn_model(dd):

    log('entered run_sn_model()')
    data_dict = await dd

    url_parameters = data_dict["inputs"].get(
        "url_parameters", {"source_name": default_source_name, "fix_z": default_fix_z}
    )

    source_name = url_parameters.get("source_name")
    fix_z = url_parameters.get("fix_z") in [True, "True", "t", "true"]
    log(f"source_name={source_name} fix_z={fix_z}")

    data = Table.read(data_dict["inputs"]["photometry"], format='ascii.csv')
    data.rename_column('mjd', 'time')
    data.rename_column('filter', 'band')
    data.rename_column('magsys', 'zpsys')

    data['flux'].fill_value = 1e-6
    data = data.filled()
    data.sort("time")

    redshift = Table.read(data_dict["inputs"]["redshift"], format='ascii.csv')
    z = redshift['redshift'][0]

    time.sleep(5)
    model = sncosmo.Model(source=source_name)

    log(f'{z=}')
    if fix_z and z is not None:
        model.set(z=z)
        bounds = {'z': (z, z)}
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

    _ = sncosmo.plot_lc(
        data,
        model=fitted_model,
        errors=result.errors,
        model_label=source_name,
        zp=23.9,
        figtext=data_dict["resource_id"],
        fname='/tmp/lc.png',
    )
    log('made lightcurve plot')


@app.route('/analysis/demo_analysis', methods=['POST'])
async def demo_analysis():
    log('entered demo_analysis()')
    log(f'{request.method} {request.url}')
    data_dict = request.get_json(silent=True)

    runner = functools.partial(run_sn_model, data_dict)

    app.add_background_task(runner)

    return "True"


if __name__ == "__main__":
    app.run(port=cfg['sn_analysis_service.port'])
