import functools
import time
import sys

import matplotlib

from quart import Quart
from quart import request
from astropy.table import Table
import sncosmo

matplotlib.use('Agg')

app = Quart(__name__)
app.debug = True


async def run_sn_model(dd, set_z=False, source_name="nugent-sn2p"):

    print('entered run_sn_model()', file=sys.stderr)
    data_dict = await dd

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

    print(f'{z=}', file=sys.stderr)
    if set_z and z is not None:
        model.set(z=z)

    # run the fit
    result, fitted_model = sncosmo.fit_lc(
        data,
        model,
        ['t0', 'amplitude'],
    )
    print("Number of chi^2 function calls:", result.ncall, file=sys.stderr)
    print("Number of degrees of freedom in fit:", result.ndof, file=sys.stderr)
    print("chi^2 value at minimum:", result.chisq, file=sys.stderr)
    print("model parameters:", result.param_names, file=sys.stderr)
    print("best-fit values:", result.parameters, file=sys.stderr)
    print(
        "The result contains the following attributes:\n",
        result.keys(),
        file=sys.stderr,
    )
    print(f'{result["success"]=}', file=sys.stderr)

    _ = sncosmo.plot_lc(
        data,
        model=fitted_model,
        errors=result.errors,
        model_label=source_name,
        zp=23.9,
        figtext=data_dict["resource_id"],
        fname='/tmp/lc.png',
    )


@app.route('/analysis/demo_analysis', methods=['POST'])
async def demo_analysis():
    print('entered demo_analysis()', file=sys.stderr)
    print(f'{request.method} {request.url}', file=sys.stderr)
    data_dict = request.get_json(silent=True)

    runner = functools.partial(run_sn_model, data_dict, set_z=True)

    app.add_background_task(runner)

    return "True"


if __name__ == "__main__":
    app.run(port=6801)
