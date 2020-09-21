from astropy import cosmology
from astropy import units as u

from baselayer.log import make_log

log = make_log('cosmology')


def establish_cosmology(cfg={}, fallback_cosmology=cosmology.Planck18_arXiv_v2):
    def _get_cosmology():
        if cfg.get('misc'):
            if cfg["misc"].get('cosmology'):
                if cfg["misc"]["cosmology"] in cosmology.parameters.available:
                    cosmo = cosmology.default_cosmology.get_cosmology_from_string(
                        cfg["misc"]["cosmology"]
                    )
                elif isinstance(cfg["misc"]["cosmology"], dict):
                    par = cfg["misc"]["cosmology"]
                    try:
                        if par.get('flat'):
                            cosmo = cosmology.FlatLambdaCDM(
                                par['H0'],
                                par['Om0'],
                                Tcmb0=par.get('Tcmb0', 2.725),
                                Neff=par.get('Neff', 3.04),
                                m_nu=u.Quantity(par.get('m_nu', [0.0, 0.0, 0.0]), u.eV),
                                name=par.get("name", "user_cosmology"),
                                Ob0=par.get('Ob0', 0.0455),
                            )
                        else:
                            cosmo = cosmology.LambdaCDM(
                                par['H0'],
                                par['Om0'],
                                par['Ode0'],
                                Tcmb0=par.get('Tcmb0', 2.725),
                                Neff=par.get('Neff', 3.04),
                                m_nu=u.Quantity(par.get('m_nu', [0.0, 0.0, 0.0]), u.eV),
                                name=par.get("name", "user_cosmology"),
                                Ob0=par.get('Ob0', 0.0455),
                            )
                    except (KeyError, NameError) as e:
                        log(f'{e}')
                        log('exception in determining user defined cosmology')
                        cosmo = fallback_cosmology
                else:
                    log(
                        'cosmology: dont know how to deal with the user supplied cosmology'
                    )
                    cosmo = fallback_cosmology
        else:
            cosmo = fallback_cosmology

        log(f'using {cosmo.name} for cosmological calculations')
        log(f'{cosmo}')
        return cosmo

    try:
        return _get_cosmology()
    except Exception:
        log(f'Error setting cosmology using {fallback_cosmology.name} as a fallback')
        return fallback_cosmology
