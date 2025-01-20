from astropy import cosmology
from astropy import units as u

from baselayer.app.env import load_env
from baselayer.log import make_log

log = make_log("cosmology")
_, cfg = load_env()


def establish_cosmology(cfg=cfg):
    user_cosmo = cfg["misc"]["cosmology"]

    if user_cosmo in cosmology.realizations.available:
        cosmo = getattr(cosmology, user_cosmo)

    elif isinstance(user_cosmo, dict):
        try:
            if user_cosmo.get("flat"):
                cosmo = cosmology.FlatLambdaCDM(
                    user_cosmo["H0"],
                    user_cosmo["Om0"],
                    Tcmb0=user_cosmo.get("Tcmb0", 2.725),
                    Neff=user_cosmo.get("Neff", 3.04),
                    m_nu=u.Quantity(user_cosmo.get("m_nu", [0.0, 0.0, 0.0]), u.eV),
                    name=user_cosmo.get("name", "user_cosmology"),
                    Ob0=user_cosmo.get("Ob0", 0.0455),
                )
            else:
                cosmo = cosmology.LambdaCDM(
                    user_cosmo["H0"],
                    user_cosmo["Om0"],
                    user_cosmo["Ode0"],
                    Tcmb0=user_cosmo.get("Tcmb0", 2.725),
                    Neff=user_cosmo.get("Neff", 3.04),
                    m_nu=u.Quantity(user_cosmo.get("m_nu", [0.0, 0.0, 0.0]), u.eV),
                    name=user_cosmo.get("name", "user_cosmology"),
                    Ob0=user_cosmo.get("Ob0", 0.0455),
                )
        except (KeyError, NameError) as e:
            log(f"{e}")
            log("Exception while processing user-defined cosmology")
            raise RuntimeError("Error parsing user-defined cosmology")

    else:
        log(f"Invalid user-defined cosmology [{user_cosmo}]")
        log(f"Try setting it to one of [{cosmology.realizations.available}]")
        raise RuntimeError("No valid cosmology specified")

    log(f"Using {cosmo.name} for cosmological calculations")
    log(f"{cosmo}")

    return cosmo
