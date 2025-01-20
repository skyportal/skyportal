__all__ = ["cosmo"]

from baselayer.app.env import load_env

from ..utils.cosmology import establish_cosmology

_, cfg = load_env()
cosmo = establish_cosmology(cfg)
