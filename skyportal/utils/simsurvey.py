import numpy as np

from ..models import (
    cosmo,
)


def get_simsurvey_parameters(model_name, optional_injection_parameters):
    """Get the simsurvey injection model parameters
    Parameters
    ----------
    model_name : str
        Model to simulate efficiency for. Must be one of kilonova, afterglow, or linear. Defaults to kilonova.
    optional_injection_parameters: dict
        Optional parameters to specify the injection type, along with a list of possible values (to be used in a dropdown UI)
    """

    if model_name == "kilonova":
        # default taken from https://github.com/mbulla/kilonova_models
        parameters = {
            "injection_filename": "data/nsns_nph1.0e+06_mejdyn0.020_mejwind0.130_phi30.txt"
        }
    elif model_name == "afterglow":
        parameters = {
            "ntime": 30,
            "t_i": 0.25,
            "t_f": 15.25,
            "nlambda": 100,
            "lambda_min": 1000,
            "lambda_max": 25000,
            "jetType": 0,
            "specType": 0,
            "thetaObs": 0.0,
            "log10_E0": 53.0,
            "thetaCore": np.pi / 4.0,
            "thetaWing": np.pi / 4.0,
            "b": 0.0,
            "log10_n0": 1.0,
            "p": 2.5,
            "log10_epsilon_e": -1,
            "log10_epsilon_B": -2,
            "d_L": 3.09e19,
            "xi_N": 1.0,
            "z": 0.0,
        }
    elif model_name == "linear":
        parameters = {
            "ntime": 30,
            "t_i": 0.25,
            "t_f": 15.25,
            "nlambda": 100,
            "lambda_min": 1000,
            "lambda_max": 25000,
            "mag": -16.0,
            "dmag": 1.0,
        }
    parameters.update(optional_injection_parameters)

    if model_name == "afterglow":
        parameters["E0"] = 10 ** parameters["log10_E0"]
        parameters["n0"] = 10 ** parameters["log10_n0"]
        parameters["epsilon_e"] = 10 ** parameters["log10_epsilon_e"]
        parameters["epsilon_B"] = 10 ** parameters["log10_epsilon_B"]

    return parameters


def random_parameters_notheta(redshifts, model, r_v=2.0, ebv_rate=0.11, **kwargs):
    """Convert distance to amplitude
    Parameters
    ----------
    redshifts : list
        List of redshifts to convert to scaling amplitude
    model : sncosmo.Model
        A sncosmo.Model to transform
    """

    # Amplitude
    amp = []
    for z in redshifts:
        amp.append(10 ** (-0.4 * cosmo.distmod(z).value))

    return {"amplitude": np.array(amp)}
